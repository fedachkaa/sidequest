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
const persistenceWarning = document.querySelector('#persistence-warning')

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
let isCompleting = false
let isInitializing = true
let progress = Progress.emptyProgress()
let initializationPromise = null

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

function setSelectedValue(name, value) {
    const option = form.querySelector(`input[name="${name}"][value="${value}"]`)
    if (option) {
        option.checked = true
    }
}

function showPersistenceWarning(message) {
    persistenceWarning.textContent = message
    persistenceWarning.hidden = false
}

async function responseError(response, fallback) {
    try {
        const payload = await response.json()
        return new Error(Progress.errorMessage(payload.detail?.code, fallback))
    } catch (error) {
        return new Error(fallback)
    }
}

async function fetchQuest(request) {
    const response = await fetch('/api/quests/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
    })

    if (!response.ok) {
        throw await responseError(response, 'The machine received an unexpected response.')
    }

    const quest = await response.json()
    if (!isQuest(quest)) {
        throw new Error('The quest came back incomplete, so it was not printed.')
    }

    return quest
}

async function fetchProgress() {
    const response = await fetch('/api/progress')
    if (!response.ok) {
        throw await responseError(response, 'The field record could not be loaded.')
    }
    return response.json()
}

async function fetchQuestStatus(questId) {
    const response = await fetch(`/api/quests/${encodeURIComponent(questId)}`)
    if (!response.ok) {
        throw await responseError(response, 'The quest status could not be confirmed.')
    }
    return response.json()
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
    document.querySelector('#stat-xp').textContent = progress.total_xp
    document.querySelector('#stat-quests').textContent = progress.completed_quests
    document.querySelector('#stat-minutes').textContent = progress.outside_minutes
    document.querySelector('#stat-streak').textContent = progress.current_streak

    badgeList.replaceChildren()
    Progress.BADGES.forEach((badge) => {
        const isUnlocked = progress.unlocked_badges.includes(badge.id)
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
    completeQuestButton.disabled = true
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

function restorePendingQuest(pendingQuest) {
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

async function loadProgress() {
    try {
        progress = await fetchProgress()
        persistenceWarning.hidden = true
        renderProgress()
        restorePendingQuest(progress.pending_quest)
    } catch (error) {
        showPersistenceWarning('Field record unavailable. Refresh to try again.')
    } finally {
        isInitializing = false
    }
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
    await initializationPromise
    if (!Progress.operationAvailable({ isInitializing, isGenerating, isCompleting })) {
        return
    }

    isGenerating = true
    lastRequest = request
    startLoading()

    try {
        const quest = await fetchQuest(request)
        currentQuest = quest
        showReceipt(currentQuest)
    } catch (error) {
        showError(error instanceof Error ? error : new Error('The machine could not print this quest.'))
    } finally {
        isGenerating = false
    }
}

async function completeCurrentQuest() {
    await initializationPromise
    if (
        !currentQuest ||
        !Progress.operationAvailable({ isInitializing, isGenerating, isCompleting })
    ) {
        return
    }

    isCompleting = true
    completeQuestButton.disabled = true
    generateButton.disabled = true
    doomscrollButton.disabled = true
    const completingQuest = currentQuest
    try {
        const response = await fetch(`/api/quests/${encodeURIComponent(completingQuest.id)}/complete`, {
            method: 'POST',
        })
        if (!response.ok) {
            throw new Error('Completion could not be saved. Please try again.')
        }

        const result = await response.json()
        progress = result.progress
        renderProgress()
        completeQuestButton.textContent = 'Quest logged'
        persistenceWarning.hidden = true
        const badgeMessage = result.new_badges.length > 0 ? ` · ${result.new_badges.length} badge unlocked` : ''
        completionConfirmation.textContent = `FIELD LOG UPDATED · +${result.awarded_xp} XP${badgeMessage}`
        completionConfirmation.hidden = false
        currentQuest = null
    } catch (error) {
        await reconcileCompletion(completingQuest)
    } finally {
        isCompleting = false
        generateButton.disabled = false
        doomscrollButton.disabled = false
    }
}

async function reconcileCompletion(completingQuest) {
    try {
        const savedQuest = await fetchQuestStatus(completingQuest.id)
        const resolution = Progress.completionResolution(savedQuest.status)

        if (resolution === 'completed') {
            currentQuest = null
            completeQuestButton.disabled = true
            completeQuestButton.textContent = 'Quest logged'
            completionConfirmation.textContent = 'QUEST COMPLETION CONFIRMED · FIELD LOG UPDATED'
            completionConfirmation.hidden = false
            statusMessage.textContent = 'Quest completion confirmed.'
            persistenceWarning.hidden = true
            try {
                progress = await fetchProgress()
                renderProgress()
            } catch (error) {
                showPersistenceWarning('Completion was confirmed, but progress could not be refreshed.')
            }
            return
        }

        if (resolution === 'retry') {
            currentQuest = completingQuest
            completeQuestButton.disabled = false
            showPersistenceWarning('Completion was not confirmed. Please try again.')
            return
        }

        if (resolution === 'superseded') {
            currentQuest = null
            completeQuestButton.disabled = true
            completeQuestButton.textContent = 'Quest superseded'
            statusMessage.textContent = 'This quest was replaced and is no longer eligible for completion.'
            showPersistenceWarning('This quest was superseded by a newer quest and cannot be completed.')
            return
        }

        currentQuest = completingQuest
        completeQuestButton.disabled = false
        showPersistenceWarning('The device returned an unknown quest status. Completion was not confirmed.')
    } catch (error) {
        currentQuest = completingQuest
        completeQuestButton.disabled = false
        showPersistenceWarning('Could not confirm whether completion was saved. Check the connection before retrying.')
    }
}

form.addEventListener('submit', (event) => {
    event.preventDefault()
    generateQuest(readQuestRequest())
})

retryButton.addEventListener('click', () => {
    generateQuest(lastRequest || readQuestRequest())
})

doomscrollButton.addEventListener('click', () => {
    if (isGenerating || isCompleting) {
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
initializationPromise = loadProgress()
