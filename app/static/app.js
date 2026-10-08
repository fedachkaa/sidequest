import {
    completeQuest,
    fetchProgress,
    fetchQuestStatus,
    generateQuest as requestQuest,
} from './api-client.js'
import {
    completeQuestButton,
    hideWarning,
    prepareQuestCompletion,
    renderProgress,
    setCompletionDisabled,
    showCompletion,
    showReconciledCompletion,
    showSupersededCompletion,
    showWarning,
} from './progress-ui.js'
import {
    hideReceipt,
    prepareAnotherReceipt,
    printReceipt,
    restoreReceipt,
    showReceipt,
    stopScrollFollow,
} from './receipt-ui.js'
import * as Progress from './progress-core.mjs'

const form = document.querySelector('#quest-form')
const generateButton = document.querySelector('#generate-button')
const doomscrollButton = document.querySelector('#doomscroll-button')
const statusMessage = document.querySelector('#status-message')
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
let currentQuest = null
let isGenerating = false
let isCompleting = false
let isInitializing = true
let progress = Progress.emptyProgress()
let initializationPromise = null

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

function clearLoadingTimers() {
    loadingTimers.forEach((timer) => window.clearTimeout(timer))
    loadingTimers = []
}

function startLoading() {
    stopScrollFollow()
    clearLoadingTimers()
    form.classList.add('is-loading')
    generateButton.disabled = true
    doomscrollButton.disabled = true
    setCompletionDisabled(true)
    hideReceipt()
    errorPanel.hidden = true
    loadingMessages.forEach(([delay, message]) => {
        loadingTimers.push(
            window.setTimeout(() => {
                statusMessage.textContent = message
            }, delay),
        )
    })
}

function finishLoading() {
    clearLoadingTimers()
    form.classList.remove('is-loading')
    generateButton.disabled = false
    doomscrollButton.disabled = false
}

function displayQuest(quest) {
    finishLoading()
    statusMessage.textContent = 'Quest printed. Take it outside.'
    prepareQuestCompletion()
    errorPanel.hidden = true
    showReceipt(quest)
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
    prepareQuestCompletion()
    restoreReceipt(pendingQuest)
    statusMessage.textContent = 'Unfinished quest restored. Ready when you return.'
}

async function loadProgress() {
    try {
        progress = await fetchProgress()
        hideWarning()
        renderProgress(progress)
        restorePendingQuest(progress.pending_quest)
    } catch (error) {
        showWarning('Field record unavailable. Refresh to try again.')
    } finally {
        isInitializing = false
    }
}

function showError(error) {
    stopScrollFollow()
    finishLoading()
    statusMessage.textContent = 'Output interrupted. Ready to retry.'
    hideReceipt()
    errorMessage.textContent = error.message
    errorPanel.hidden = false
    errorPanel.scrollIntoView({ behavior: 'smooth', block: 'center' })
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
        currentQuest = await requestQuest(request)
        displayQuest(currentQuest)
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
    setCompletionDisabled(true)
    generateButton.disabled = true
    doomscrollButton.disabled = true
    const completingQuest = currentQuest

    try {
        const result = await completeQuest(completingQuest.id)
        progress = result.progress
        renderProgress(progress)
        showCompletion(result)
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
            showReconciledCompletion()
            statusMessage.textContent = 'Quest completion confirmed.'
            try {
                progress = await fetchProgress()
                renderProgress(progress)
            } catch (error) {
                showWarning('Completion was confirmed, but progress could not be refreshed.')
            }
            return
        }

        if (resolution === 'retry') {
            currentQuest = completingQuest
            setCompletionDisabled(false)
            showWarning('Completion was not confirmed. Please try again.')
            return
        }

        if (resolution === 'superseded') {
            currentQuest = null
            showSupersededCompletion()
            statusMessage.textContent = 'This quest was replaced and is no longer eligible for completion.'
            return
        }

        currentQuest = completingQuest
        setCompletionDisabled(false)
        showWarning('The device returned an unknown quest status. Completion was not confirmed.')
    } catch (error) {
        currentQuest = completingQuest
        setCompletionDisabled(false)
        showWarning('Could not confirm whether completion was saved. Check the connection before retrying.')
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
printReceiptButton.addEventListener('click', printReceipt)

anotherQuestButton.addEventListener('click', () => {
    prepareAnotherReceipt()
    statusMessage.textContent = 'Selections retained. Ready for another.'
    generateButton.focus()
    form.scrollIntoView({ behavior: 'smooth', block: 'start' })
})

window.addEventListener('beforeprint', stopScrollFollow)

renderProgress(progress)
initializationPromise = loadProgress()
