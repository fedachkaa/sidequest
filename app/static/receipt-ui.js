const receiptStage = document.querySelector('#receipt-stage')
const receiptViewport = document.querySelector('#receipt-viewport')
const receipt = document.querySelector('#receipt')
const scrollCancelEvents = ['wheel', 'touchstart', 'pointerdown', 'keydown']

let scrollFollowFrame = null

export function renderReceipt(quest) {
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

export function showReceipt(quest) {
    renderReceipt(quest)
    receiptStage.hidden = false
    dispenseReceipt()
}

export function restoreReceipt(quest) {
    renderReceipt(quest)
    receiptStage.classList.remove('is-printing')
    receiptViewport.style.height = 'auto'
    receiptStage.hidden = false
}

export function hideReceipt() {
    receiptStage.hidden = true
}

export function prepareAnotherReceipt() {
    stopScrollFollow()
    receiptViewport.removeEventListener('transitionend', finishDispensing)
    receiptStage.hidden = true
    receiptStage.classList.remove('is-printing')
    receiptViewport.style.removeProperty('height')
}

export function printReceipt() {
    stopScrollFollow()
    window.print()
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

export function stopScrollFollow() {
    if (scrollFollowFrame !== null) {
        window.cancelAnimationFrame(scrollFollowFrame)
        scrollFollowFrame = null
    }

    scrollCancelEvents.forEach((eventName) => {
        window.removeEventListener(eventName, stopScrollFollow)
    })
}
