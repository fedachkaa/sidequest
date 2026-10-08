import { errorMessage } from './progress-core.mjs'

async function responseError(response, fallback) {
    try {
        const payload = await response.json()
        return new Error(errorMessage(payload.detail?.code, fallback))
    } catch (error) {
        return new Error(fallback)
    }
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

export async function generateQuest(request) {
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

export async function fetchProgress() {
    const response = await fetch('/api/progress')
    if (!response.ok) {
        throw await responseError(response, 'The field record could not be loaded.')
    }
    return response.json()
}

export async function fetchQuestStatus(questId) {
    const response = await fetch(`/api/quests/${encodeURIComponent(questId)}`)
    if (!response.ok) {
        throw await responseError(response, 'The quest status could not be confirmed.')
    }
    return response.json()
}

export async function completeQuest(questId) {
    const response = await fetch(`/api/quests/${encodeURIComponent(questId)}/complete`, {
        method: 'POST',
    })
    if (!response.ok) {
        throw await responseError(response, 'Completion could not be saved. Please try again.')
    }
    return response.json()
}
