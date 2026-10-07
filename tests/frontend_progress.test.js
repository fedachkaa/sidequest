const test = require('node:test')
const assert = require('node:assert/strict')

require('../app/static/progress.js')

const Progress = globalThis.SidequestProgress

function quest(overrides = {}) {
    return {
        id: 'quest-1',
        duration_minutes: 30,
        environment: 'city',
        mode: 'explore',
        ...overrides,
    }
}

function memoryStorage() {
    const values = new Map()
    return {
        getItem: (key) => values.get(key) ?? null,
        setItem: (key, value) => values.set(key, value),
        removeItem: (key) => values.delete(key),
    }
}

test('calculates XP from quest duration', () => {
    assert.equal(Progress.xpForDuration(15), 50)
    assert.equal(Progress.xpForDuration(30), 100)
    assert.equal(Progress.xpForDuration(60), 200)
})

test('first completion updates progress and unlocks first steps', () => {
    const result = Progress.completeQuest(
        Progress.emptyProgress(),
        quest(),
        new Date(2026, 9, 7, 18),
    )

    assert.equal(result.awarded, true)
    assert.equal(result.xpAwarded, 100)
    assert.equal(result.progress.completedQuests, 1)
    assert.equal(result.progress.outsideMinutes, 30)
    assert.equal(result.progress.currentStreak, 1)
    assert.deepEqual(result.newBadges, ['first-steps'])
})

test('does not award the same quest twice', () => {
    const first = Progress.completeQuest(Progress.emptyProgress(), quest(), new Date(2026, 9, 7))
    const duplicate = Progress.completeQuest(first.progress, quest(), new Date(2026, 9, 7))

    assert.equal(duplicate.awarded, false)
    assert.strictEqual(duplicate.progress, first.progress)
})

test('same-day completion keeps the current streak', () => {
    const progress = { ...Progress.emptyProgress(), currentStreak: 4, lastCompletionDate: '2026-10-07' }
    const result = Progress.completeQuest(progress, quest(), new Date(2026, 9, 7, 23))

    assert.equal(result.progress.currentStreak, 4)
})

test('consecutive-day completion increments the streak', () => {
    const progress = { ...Progress.emptyProgress(), currentStreak: 2, lastCompletionDate: '2026-10-07' }
    const result = Progress.completeQuest(progress, quest(), new Date(2026, 9, 8))

    assert.equal(result.progress.currentStreak, 3)
    assert.equal(result.progress.bestStreak, 3)
})

test('a missed day expires the visible streak and resets on completion', () => {
    const progress = { ...Progress.emptyProgress(), currentStreak: 5, bestStreak: 5, lastCompletionDate: '2026-10-05' }

    assert.equal(Progress.visibleStreak(progress, '2026-10-07'), 0)
    const result = Progress.completeQuest(progress, quest(), new Date(2026, 9, 7))
    assert.equal(result.progress.currentStreak, 1)
    assert.equal(result.progress.bestStreak, 5)
})

test('calendar day distance handles month and year boundaries', () => {
    assert.equal(Progress.calendarDayDistance('2026-01-31', '2026-02-01'), 1)
    assert.equal(Progress.calendarDayDistance('2026-12-31', '2027-01-01'), 1)
})

test('unlocks all six badges at their thresholds', () => {
    const progress = {
        ...Progress.emptyProgress(),
        completedQuests: 10,
        outsideMinutes: 60,
        currentStreak: 3,
        environmentCounts: { city: 4, park: 3, nature: 3 },
    }

    assert.equal(Progress.BADGES.length, 6)
    assert.deepEqual(Progress.earnedBadgeIds(progress), Progress.BADGES.map((badge) => badge.id))
})

test('malformed and unavailable storage return safe default progress', () => {
    const malformedStorage = { getItem: () => '{not json' }
    const unavailableStorage = { getItem: () => { throw new Error('blocked') } }

    assert.deepEqual(Progress.loadProgress(malformedStorage), Progress.emptyProgress())
    assert.deepEqual(Progress.loadProgress(unavailableStorage), Progress.emptyProgress())
    assert.equal(Progress.saveProgress({ setItem: () => { throw new Error('full') } }, {}), false)
})

test('doomscroll escape uses the fixed immediate request parameters', () => {
    assert.deepEqual(Progress.doomscrollRequest(), {
        duration_minutes: 15,
        environment: 'anywhere',
        mode: 'surprise',
    })
})

test('saves and restores a pending quest', () => {
    const storage = memoryStorage()
    const pendingQuest = quest({
        title: 'Urban Detective',
        difficulty: 2,
        category: 'exploration',
        tasks: ['One', 'Two', 'Three'],
    })

    assert.equal(Progress.savePendingQuest(storage, pendingQuest), true)
    assert.deepEqual(Progress.loadPendingQuest(storage), pendingQuest)
    assert.deepEqual(
        Progress.restorablePendingQuest(Progress.emptyProgress(), pendingQuest),
        pendingQuest,
    )
})

test('a newly generated pending quest replaces the previous one', () => {
    const storage = memoryStorage()
    const firstQuest = quest({
        title: 'First',
        difficulty: 1,
        category: 'calm',
        tasks: ['One', 'Two', 'Three'],
    })
    const replacementQuest = { ...firstQuest, id: 'quest-2', title: 'Replacement' }

    Progress.savePendingQuest(storage, firstQuest)
    Progress.savePendingQuest(storage, replacementQuest)

    assert.deepEqual(Progress.loadPendingQuest(storage), replacementQuest)
})

test('completed quests are not restored and pending storage can be cleared', () => {
    const storage = memoryStorage()
    const pendingQuest = quest({
        title: 'Completed',
        difficulty: 1,
        category: 'move',
        tasks: ['One', 'Two', 'Three'],
    })
    const completedProgress = {
        ...Progress.emptyProgress(),
        completedQuestIds: [pendingQuest.id],
    }
    Progress.savePendingQuest(storage, pendingQuest)

    assert.equal(Progress.restorablePendingQuest(completedProgress, pendingQuest), null)
    assert.equal(Progress.clearPendingQuest(storage), true)
    assert.equal(Progress.loadPendingQuest(storage), null)
})

test('malformed pending quests and unavailable pending storage fail safely', () => {
    const malformedStorage = { getItem: () => JSON.stringify({ id: 'incomplete' }) }
    const unavailableStorage = {
        getItem: () => { throw new Error('blocked') },
        setItem: () => { throw new Error('blocked') },
        removeItem: () => { throw new Error('blocked') },
    }

    assert.equal(Progress.loadPendingQuest(malformedStorage), null)
    assert.equal(Progress.loadPendingQuest(unavailableStorage), null)
    assert.equal(Progress.savePendingQuest(unavailableStorage, quest()), false)
    assert.equal(Progress.clearPendingQuest(unavailableStorage), false)
})
