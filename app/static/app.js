const Progress = globalThis.SidequestProgress
const form = document.querySelector('#quest-form')
const generateButton = document.querySelector('#generate-button')
const doomscrollButton = document.querySelector('#doomscroll-button')
const statusMessage = document.querySelector('#status-message')
const receiptStage = document.querySelector('#receipt-stage')
const receiptViewport = document.querySelector('#receipt-viewport')
const receipt = document.querySelector('#receipt')
const errorPanel = document.querySelector('#error-panel')
const errorMessage = document.querySelector('#error-message')
const retryButton = document.querySelector('#retry-button')
const printReceiptButton = document.querySelector('#print-receipt-button')
const anotherQuestButton = document.querySelector('#another-quest-button')
const completeQuestButton = document.querySelector('#complete-quest-button')
const completionConfirmation = document.querySelector('#completion-confirmation')
const badgeList = document.querySelector('#badge-list')
const storageWarning = document.querySelector('#storage-warning')

const loadingMessages = [
    [0, 'Contacting the local quest engine…'],
    [8000, 'Gemma is drafting three field objectives…'],
    [20000, 'Still generating locally. Larger quests can take a minute…'],
    [45000, 'The model is still working. Your request has not been abandoned…'],
]

let loadingTimers = []
let lastRequest = null
let scrollFollowFrame = null
let currentQuest = null
let isGenerating = false
let progress = Progress.loadProgress(getStorage())

const scrollCancelEvents = ['wheel', 'touchstart', 'pointerdown', 'keydown']

function selectedValue(name) {
    return form.elements[name].value
}

function readQuestRequest() {
    return {
        duration_minutes: Number(selectedValue('duration')),
        environment: selectedValue('environment'),
        mode: selectedValue('mode'),
    }
}

function getStorage() {
    try {
        return window.localStorage
    } catch (error) {
        return null
    }
}

function setSelectedValue(name, value) {
    const option = form.querySelector(`input[name="${name}"][value="${value}"]`)
    if (option) {
        option.checked = true
    }
}

function showStorageWarning() {
    storageWarning.hidden = false
}

async function fetchQuest(request) {
    const response = await fetch('/api/quests/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
    })

    if (!response.ok) {
        throw new Error(response.status === 503 ? 'The local quest engine is unavailable right now.' : 'The machine received an unexpected response.')
    }

    const quest = await response.json()
    if (!isQuest(quest)) {
        throw new Error('The quest came back incomplete, so it was not printed.')
    }

    return quest
}

function isQuest(quest) {
    return Boolean(
        quest &&
            typeof quest.title === 'string' &&
            Number.isInteger(quest.duration_minutes) &&
            Number.isInteger(quest.difficulty) &&
            quest.difficulty >= 1 &&
            quest.difficulty <= 3 &&
            typeof quest.category === 'string' &&
            Array.isArray(quest.tasks) &&
            quest.tasks.length === 3 &&
            quest.tasks.every((task) => typeof task === 'string'),
    )
}

function renderReceipt(quest) {
    document.querySelector('#receipt-title').textContent = quest.title
    document.querySelector('#receipt-duration').textContent = `${quest.duration_minutes} MIN`
    document.querySelector('#receipt-difficulty').textContent = `${'●'.repeat(quest.difficulty)}${'○'.repeat(3 - quest.difficulty)}`
    document.querySelector('#receipt-category').textContent = quest.category

    const tasks = document.querySelector('#receipt-tasks')
    tasks.replaceChildren()
    quest.tasks.forEach((task) => {
        const item = document.createElement('li')
        item.textContent = task
        tasks.append(item)
    })
}

function renderProgress() {
    const today = Progress.localDateString(new Date())
    document.querySelector('#stat-xp').textContent = progress.totalXp
    document.querySelector('#stat-quests').textContent = progress.completedQuests
    document.querySelector('#stat-minutes').textContent = progress.outsideMinutes
    document.querySelector('#stat-streak').textContent = Progress.visibleStreak(progress, today)

    badgeList.replaceChildren()
    Progress.BADGES.forEach((badge) => {
        const isUnlocked = progress.unlockedBadges.includes(badge.id)
        const item = document.createElement('div')
        const marker = document.createElement('span')
        const copy = document.createElement('div')
        const name = document.createElement('strong')
        const description = document.createElement('small')

        item.className = `field-badge${isUnlocked ? ' is-unlocked' : ''}`
        item.setAttribute('aria-label', `${badge.name}: ${isUnlocked ? 'unlocked' : 'locked'}. ${badge.description}`)
        marker.className = 'field-badge__marker'
        marker.textContent = isUnlocked ? '★' : '×'
        name.textContent = badge.name
        description.textContent = badge.description
        copy.append(name, description)
        item.append(marker, copy)
        badgeList.append(item)
    })
}

function startLoading() {
    stopScrollFollow()
    clearLoadingTimers()
    form.classList.add('is-loading')
    generateButton.disabled = true
    doomscrollButton.disabled = true
    receiptStage.hidden = true
    errorPanel.hidden = true
    loadingMessages.forEach(([delay, message]) => {
        loadingTimers.push(
            window.setTimeout(() => {
                statusMessage.textContent = message
            }, delay),
        )
    })
}

function showReceipt(quest) {
    clearLoadingTimers()
    form.classList.remove('is-loading')
    generateButton.disabled = false
    doomscrollButton.disabled = false
    statusMessage.textContent = 'Quest printed. Take it outside.'
    renderReceipt(quest)
    completeQuestButton.disabled = false
    completeQuestButton.textContent = 'Complete quest'
    completionConfirmation.hidden = true
    errorPanel.hidden = true
    receiptStage.hidden = false
    dispenseReceipt()
}

function restorePendingQuest() {
    const storedQuest = Progress.loadPendingQuest(getStorage())
    const pendingQuest = Progress.restorablePendingQuest(progress, storedQuest)

    if (storedQuest && !pendingQuest) {
        if (!Progress.clearPendingQuest(getStorage())) {
            showStorageWarning()
        }
        return
    }

    if (!pendingQuest) {
        return
    }

    currentQuest = pendingQuest
    lastRequest = {
        duration_minutes: pendingQuest.duration_minutes,
        environment: pendingQuest.environment,
        mode: pendingQuest.mode,
    }
    setSelectedValue('duration', String(pendingQuest.duration_minutes))
    setSelectedValue('environment', pendingQuest.environment)
    setSelectedValue('mode', pendingQuest.mode)
    renderReceipt(pendingQuest)
    completeQuestButton.disabled = false
    completeQuestButton.textContent = 'Complete quest'
    completionConfirmation.hidden = true
    receiptStage.classList.remove('is-printing')
    receiptViewport.style.height = 'auto'
    receiptStage.hidden = false
    statusMessage.textContent = 'Unfinished quest restored. Ready when you return.'
}

function dispenseReceipt() {
    receiptViewport.removeEventListener('transitionend', finishDispensing)
    receiptStage.classList.remove('is-printing')
    receiptViewport.style.removeProperty('height')
    receiptViewport.style.setProperty('--receipt-height', `${receipt.offsetHeight + 8}px`)
    void receiptViewport.offsetHeight
    receiptStage.classList.add('is-printing')
    startScrollFollow()

    receiptViewport.addEventListener('transitionend', finishDispensing)
}

function finishDispensing(event) {
    if (event.propertyName !== 'height') {
        return
    }

    receiptViewport.style.height = 'auto'
    receiptViewport.removeEventListener('transitionend', finishDispensing)
    stopScrollFollow()
}

function startScrollFollow() {
    stopScrollFollow()

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        receiptStage.scrollIntoView({ behavior: 'auto', block: 'start' })
        return
    }

    scrollCancelEvents.forEach((eventName) => {
        window.addEventListener(eventName, stopScrollFollow, { passive: true })
    })

    function followReceiptEdge() {
        const receiptBottom = receiptViewport.getBoundingClientRect().bottom
        const followLine = window.innerHeight * 0.82
        const distance = receiptBottom - followLine

        if (distance > 0) {
            const scrollStep = Math.min(24, Math.max(1, distance * 0.18))
            window.scrollBy(0, scrollStep)
        }

        scrollFollowFrame = window.requestAnimationFrame(followReceiptEdge)
    }

    scrollFollowFrame = window.requestAnimationFrame(followReceiptEdge)
}

function stopScrollFollow() {
    if (scrollFollowFrame !== null) {
        window.cancelAnimationFrame(scrollFollowFrame)
        scrollFollowFrame = null
    }

    scrollCancelEvents.forEach((eventName) => {
        window.removeEventListener(eventName, stopScrollFollow)
    })
}

function showError(error) {
    stopScrollFollow()
    clearLoadingTimers()
    form.classList.remove('is-loading')
    generateButton.disabled = false
    doomscrollButton.disabled = false
    statusMessage.textContent = 'Output interrupted. Ready to retry.'
    receiptStage.hidden = true
    errorMessage.textContent = error.message
    errorPanel.hidden = false
    errorPanel.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function clearLoadingTimers() {
    loadingTimers.forEach((timer) => window.clearTimeout(timer))
    loadingTimers = []
}

async function generateQuest(request) {
    if (isGenerating) {
        return
    }

    isGenerating = true
    lastRequest = request
    startLoading()

    try {
        const quest = await fetchQuest(request)
        currentQuest = {
            ...quest,
            id: createQuestId(),
            environment: request.environment,
            mode: request.mode,
        }
        if (!Progress.savePendingQuest(getStorage(), currentQuest)) {
            showStorageWarning()
        }
        showReceipt(currentQuest)
    } catch (error) {
        showError(error instanceof Error ? error : new Error('The machine could not print this quest.'))
    } finally {
        isGenerating = false
    }
}

function createQuestId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
        return globalThis.crypto.randomUUID()
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function completeCurrentQuest() {
    if (!currentQuest) {
        return
    }

    const result = Progress.completeQuest(progress, currentQuest, new Date())
    if (!result.awarded) {
        return
    }

    progress = result.progress
    const isProgressSaved = Progress.saveProgress(getStorage(), progress)
    const isPendingQuestCleared = Progress.clearPendingQuest(getStorage())
    if (!isProgressSaved || !isPendingQuestCleared) {
        showStorageWarning()
    }
    renderProgress()
    completeQuestButton.disabled = true
    completeQuestButton.textContent = 'Quest logged'

    const badgeMessage = result.newBadges.length > 0 ? ` · ${result.newBadges.length} badge unlocked` : ''
    completionConfirmation.textContent = `FIELD LOG UPDATED · +${result.xpAwarded} XP${badgeMessage}`
    completionConfirmation.hidden = false
}

form.addEventListener('submit', (event) => {
    event.preventDefault()
    generateQuest(readQuestRequest())
})

retryButton.addEventListener('click', () => {
    generateQuest(lastRequest || readQuestRequest())
})

doomscrollButton.addEventListener('click', () => {
    if (isGenerating) {
        return
    }

    const request = Progress.doomscrollRequest()
    setSelectedValue('duration', String(request.duration_minutes))
    setSelectedValue('environment', request.environment)
    setSelectedValue('mode', request.mode)
    generateQuest(readQuestRequest())
})

completeQuestButton.addEventListener('click', completeCurrentQuest)

printReceiptButton.addEventListener('click', () => {
    stopScrollFollow()
    window.print()
})

anotherQuestButton.addEventListener('click', () => {
    stopScrollFollow()
    receiptViewport.removeEventListener('transitionend', finishDispensing)
    receiptStage.hidden = true
    receiptStage.classList.remove('is-printing')
    receiptViewport.style.removeProperty('height')
    statusMessage.textContent = 'Selections retained. Ready for another.'
    generateButton.focus()
    form.scrollIntoView({ behavior: 'smooth', block: 'start' })
})

window.addEventListener('beforeprint', stopScrollFollow)

renderProgress()
restorePendingQuest()
