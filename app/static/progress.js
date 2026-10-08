(function initializeProgress(globalScope) {
    const BADGES = [
        { id: 'first-steps', name: 'FIRST STEPS', description: 'Complete your first quest.' },
        { id: 'touch-grass', name: 'TOUCH GRASS', description: 'Complete 3 quests.' },
        { id: 'explorer', name: 'EXPLORER', description: 'Quest in 3 environments.' },
        { id: 'momentum', name: 'MOMENTUM', description: 'Reach a 3-day streak.' },
        { id: 'outside-regular', name: 'OUTSIDE REGULAR', description: 'Complete 10 quests.' },
        { id: 'one-hour-club', name: 'ONE HOUR CLUB', description: 'Spend 60 minutes outside.' },
    ]

    function emptyProgress() {
        return {
            total_xp: 0,
            completed_quests: 0,
            outside_minutes: 0,
            current_streak: 0,
            best_streak: 0,
            last_completion_date: '',
            unlocked_badges: [],
            pending_quest: null,
        }
    }

    function doomscrollRequest() {
        return {
            duration_minutes: 15,
            environment: 'anywhere',
            mode: 'surprise',
        }
    }

    function operationAvailable(state) {
        return !state.isInitializing && !state.isGenerating && !state.isCompleting
    }

    function isSamePendingQuest(pendingQuest, questId) {
        return Boolean(pendingQuest && pendingQuest.id === questId)
    }

    globalScope.SidequestProgress = {
        BADGES,
        emptyProgress,
        doomscrollRequest,
        operationAvailable,
        isSamePendingQuest,
    }
})(typeof globalThis === 'undefined' ? window : globalThis)
