const form = document.querySelector('#quest-form')
const generateButton = document.querySelector('#generate-button')
const statusMessage = document.querySelector('#status-message')
const receiptStage = document.querySelector('#receipt-stage')
const receiptViewport = document.querySelector('#receipt-viewport')
const receipt = document.querySelector('#receipt')
const errorPanel = document.querySelector('#error-panel')
const errorMessage = document.querySelector('#error-message')
const retryButton = document.querySelector('#retry-button')
const printReceiptButton = document.querySelector('#print-receipt-button')
const anotherQuestButton = document.querySelector('#another-quest-button')

const loadingMessages = [
    [0, 'Contacting the local quest engine…'],
    [8000, 'Gemma is drafting three field objectives…'],
    [20000, 'Still generating locally. Larger quests can take a minute…'],
    [45000, 'The model is still working. Your request has not been abandoned…'],
]

let loadingTimers = []
let lastRequest = null
let scrollFollowFrame = null

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

function startLoading() {
    stopScrollFollow()
    clearLoadingTimers()
    form.classList.add('is-loading')
    generateButton.disabled = true
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
    statusMessage.textContent = 'Quest printed. Take it outside.'
    renderReceipt(quest)
    errorPanel.hidden = true
    receiptStage.hidden = false
    dispenseReceipt()
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
    lastRequest = request
    startLoading()

    try {
        const quest = await fetchQuest(request)
        showReceipt(quest)
    } catch (error) {
        showError(error instanceof Error ? error : new Error('The machine could not print this quest.'))
    }
}

form.addEventListener('submit', (event) => {
    event.preventDefault()
    generateQuest(readQuestRequest())
})

retryButton.addEventListener('click', () => {
    generateQuest(lastRequest || readQuestRequest())
})

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
