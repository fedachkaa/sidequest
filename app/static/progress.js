(function initializeProgress(globalScope) {
    const STORAGE_KEY = 'sidequest.progress.v1'
    const PENDING_QUEST_KEY = 'sidequest.pendingQuest.v1'

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
            totalXp: 0,
            completedQuests: 0,
            outsideMinutes: 0,
            currentStreak: 0,
            bestStreak: 0,
            lastCompletionDate: '',
            unlockedBadges: [],
            completedQuestIds: [],
            environmentCounts: {},
            modeCounts: {},
        }
    }

    function xpForDuration(durationMinutes) {
        return { 15: 50, 30: 100, 60: 200 }[durationMinutes] || 0
    }

    function doomscrollRequest() {
        return {
            duration_minutes: 15,
            environment: 'anywhere',
            mode: 'surprise',
        }
    }

    function localDateString(date) {
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
    }

    function calendarDayDistance(fromDate, toDate) {
        if (!fromDate || !toDate) {
            return null
        }

        const fromParts = fromDate.split('-').map(Number)
        const toParts = toDate.split('-').map(Number)
        if (fromParts.length !== 3 || toParts.length !== 3 || [...fromParts, ...toParts].some(Number.isNaN)) {
            return null
        }

        const fromDay = Date.UTC(fromParts[0], fromParts[1] - 1, fromParts[2])
        const toDay = Date.UTC(toParts[0], toParts[1] - 1, toParts[2])
        return Math.round((toDay - fromDay) / 86400000)
    }

    function nextStreak(currentStreak, lastCompletionDate, completionDate) {
        const distance = calendarDayDistance(lastCompletionDate, completionDate)
        if (distance === 0) {
            return currentStreak
        }
        if (distance === 1) {
            return currentStreak + 1
        }
        return 1
    }

    function visibleStreak(progress, today) {
        const distance = calendarDayDistance(progress.lastCompletionDate, today)
        return distance === 0 || distance === 1 ? progress.currentStreak : 0
    }

    function earnedBadgeIds(progress) {
        const environments = Object.values(progress.environmentCounts).filter((count) => count > 0).length
        return BADGES.filter((badge) => {
            const conditions = {
                'first-steps': progress.completedQuests >= 1,
                'touch-grass': progress.completedQuests >= 3,
                explorer: environments >= 3,
                momentum: progress.currentStreak >= 3,
                'outside-regular': progress.completedQuests >= 10,
                'one-hour-club': progress.outsideMinutes >= 60,
            }
            return conditions[badge.id]
        }).map((badge) => badge.id)
    }

    function completeQuest(progress, quest, completionDate) {
        if (progress.completedQuestIds.includes(quest.id)) {
            return { progress, awarded: false, xpAwarded: 0, newBadges: [] }
        }

        const date = localDateString(completionDate)
        const streak = nextStreak(progress.currentStreak, progress.lastCompletionDate, date)
        const updated = {
            ...progress,
            totalXp: progress.totalXp + xpForDuration(quest.duration_minutes),
            completedQuests: progress.completedQuests + 1,
            outsideMinutes: progress.outsideMinutes + quest.duration_minutes,
            currentStreak: streak,
            bestStreak: Math.max(progress.bestStreak, streak),
            lastCompletionDate: date,
            completedQuestIds: [...progress.completedQuestIds, quest.id],
            environmentCounts: incrementCount(progress.environmentCounts, quest.environment),
            modeCounts: incrementCount(progress.modeCounts, quest.mode),
        }
        const earned = earnedBadgeIds(updated)
        const newBadges = earned.filter((badgeId) => !progress.unlockedBadges.includes(badgeId))
        updated.unlockedBadges = [...new Set([...progress.unlockedBadges, ...earned])]

        return {
            progress: updated,
            awarded: true,
            xpAwarded: xpForDuration(quest.duration_minutes),
            newBadges,
        }
    }

    function incrementCount(counts, key) {
        return { ...counts, [key]: (counts[key] || 0) + 1 }
    }

    function loadProgress(storage) {
        try {
            const parsed = JSON.parse(storage.getItem(STORAGE_KEY))
            return normalizeProgress(parsed)
        } catch (error) {
            return emptyProgress()
        }
    }

    function saveProgress(storage, progress) {
        try {
            storage.setItem(STORAGE_KEY, JSON.stringify(progress))
            return true
        } catch (error) {
            return false
        }
    }

    function loadPendingQuest(storage) {
        try {
            return normalizePendingQuest(JSON.parse(storage.getItem(PENDING_QUEST_KEY)))
        } catch (error) {
            return null
        }
    }

    function savePendingQuest(storage, quest) {
        try {
            storage.setItem(PENDING_QUEST_KEY, JSON.stringify(quest))
            return true
        } catch (error) {
            return false
        }
    }

    function clearPendingQuest(storage) {
        try {
            storage.removeItem(PENDING_QUEST_KEY)
            return true
        } catch (error) {
            return false
        }
    }

    function restorablePendingQuest(progress, pendingQuest) {
        if (!pendingQuest || progress.completedQuestIds.includes(pendingQuest.id)) {
            return null
        }
        return pendingQuest
    }

    function normalizePendingQuest(value) {
        const validDurations = [15, 30, 60]
        const validEnvironments = ['city', 'park', 'nature', 'anywhere']
        const validModes = ['calm', 'move', 'explore', 'surprise']
        const isValid =
            value &&
            typeof value === 'object' &&
            typeof value.id === 'string' &&
            value.id.length > 0 &&
            typeof value.title === 'string' &&
            validDurations.includes(value.duration_minutes) &&
            Number.isInteger(value.difficulty) &&
            value.difficulty >= 1 &&
            value.difficulty <= 3 &&
            typeof value.category === 'string' &&
            Array.isArray(value.tasks) &&
            value.tasks.length === 3 &&
            value.tasks.every((task) => typeof task === 'string') &&
            validEnvironments.includes(value.environment) &&
            validModes.includes(value.mode)

        return isValid ? value : null
    }

    function normalizeProgress(value) {
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
            return emptyProgress()
        }

        const defaults = emptyProgress()
        return {
            totalXp: nonNegativeNumber(value.totalXp, defaults.totalXp),
            completedQuests: nonNegativeNumber(value.completedQuests, defaults.completedQuests),
            outsideMinutes: nonNegativeNumber(value.outsideMinutes, defaults.outsideMinutes),
            currentStreak: nonNegativeNumber(value.currentStreak, defaults.currentStreak),
            bestStreak: nonNegativeNumber(value.bestStreak, defaults.bestStreak),
            lastCompletionDate: typeof value.lastCompletionDate === 'string' ? value.lastCompletionDate : '',
            unlockedBadges: validStringArray(value.unlockedBadges),
            completedQuestIds: validStringArray(value.completedQuestIds),
            environmentCounts: validCounts(value.environmentCounts),
            modeCounts: validCounts(value.modeCounts),
        }
    }

    function nonNegativeNumber(value, fallback) {
        return Number.isFinite(value) && value >= 0 ? value : fallback
    }

    function validStringArray(value) {
        return Array.isArray(value) ? value.filter((item) => typeof item === 'string') : []
    }

    function validCounts(value) {
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
            return {}
        }

        return Object.fromEntries(
            Object.entries(value).filter(([, count]) => Number.isFinite(count) && count >= 0),
        )
    }

    globalScope.SidequestProgress = {
        STORAGE_KEY,
        PENDING_QUEST_KEY,
        BADGES,
        emptyProgress,
        xpForDuration,
        doomscrollRequest,
        localDateString,
        calendarDayDistance,
        nextStreak,
        visibleStreak,
        earnedBadgeIds,
        completeQuest,
        loadProgress,
        saveProgress,
        loadPendingQuest,
        savePendingQuest,
        clearPendingQuest,
        restorablePendingQuest,
    }
})(typeof globalThis === 'undefined' ? window : globalThis)
