import { BADGES } from './progress-core.mjs'
const badgeList = document.querySelector('#badge-list')
const persistenceWarning = document.querySelector('#persistence-warning')
const completeQuestButton = document.querySelector('#complete-quest-button')
const completionConfirmation = document.querySelector('#completion-confirmation')

export function renderProgress(progress) {
    document.querySelector('#stat-xp').textContent = progress.total_xp
    document.querySelector('#stat-quests').textContent = progress.completed_quests
    document.querySelector('#stat-minutes').textContent = progress.outside_minutes
    document.querySelector('#stat-streak').textContent = progress.current_streak

    badgeList.replaceChildren()
    BADGES.forEach((badge) => {
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

export function prepareQuestCompletion() {
    completeQuestButton.disabled = false
    completeQuestButton.textContent = 'Complete quest'
    completionConfirmation.hidden = true
}

export function setCompletionDisabled(isDisabled) {
    completeQuestButton.disabled = isDisabled
}

export function showCompletion(result) {
    completeQuestButton.textContent = 'Quest logged'
    hideWarning()
    const badgeMessage = result.new_badges.length > 0 ? ` · ${result.new_badges.length} badge unlocked` : ''
    completionConfirmation.textContent = `FIELD LOG UPDATED · +${result.awarded_xp} XP${badgeMessage}`
    completionConfirmation.hidden = false
}

export function showReconciledCompletion() {
    completeQuestButton.disabled = true
    completeQuestButton.textContent = 'Quest logged'
    completionConfirmation.textContent = 'QUEST COMPLETION CONFIRMED · FIELD LOG UPDATED'
    completionConfirmation.hidden = false
    hideWarning()
}

export function showSupersededCompletion() {
    completeQuestButton.disabled = true
    completeQuestButton.textContent = 'Quest superseded'
    showWarning('This quest was superseded by a newer quest and cannot be completed.')
}

export function showWarning(message) {
    persistenceWarning.textContent = message
    persistenceWarning.hidden = false
}

export function hideWarning() {
    persistenceWarning.hidden = true
}

export { completeQuestButton }
