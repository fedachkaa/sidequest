const test = require('node:test')
const assert = require('node:assert/strict')

require('../app/static/progress.js')

const Progress = globalThis.SidequestProgress

test('provides the backend progress empty state shape', () => {
    assert.deepEqual(Progress.emptyProgress(), {
        total_xp: 0,
        completed_quests: 0,
        outside_minutes: 0,
        current_streak: 0,
        best_streak: 0,
        last_completion_date: '',
        unlocked_badges: [],
        pending_quest: null,
    })
})

test('renders exactly the six backend badge identifiers', () => {
    assert.deepEqual(
        Progress.BADGES.map((badge) => badge.id),
        [
            'first-steps',
            'touch-grass',
            'explorer',
            'momentum',
            'outside-regular',
            'one-hour-club',
        ],
    )
})

test('doomscroll escape keeps its fixed API request parameters', () => {
    assert.deepEqual(Progress.doomscrollRequest(), {
        duration_minutes: 15,
        environment: 'anywhere',
        mode: 'surprise',
    })
})

test('generation and completion are unavailable during initialization or another mutation', () => {
    assert.equal(
        Progress.operationAvailable({ isInitializing: true, isGenerating: false, isCompleting: false }),
        false,
    )
    assert.equal(
        Progress.operationAvailable({ isInitializing: false, isGenerating: true, isCompleting: false }),
        false,
    )
    assert.equal(
        Progress.operationAvailable({ isInitializing: false, isGenerating: false, isCompleting: true }),
        false,
    )
    assert.equal(
        Progress.operationAvailable({ isInitializing: false, isGenerating: false, isCompleting: false }),
        true,
    )
})

test('completion reconciliation identifies whether the attempted quest remains pending', () => {
    assert.equal(Progress.isSamePendingQuest({ id: 'quest-1' }, 'quest-1'), true)
    assert.equal(Progress.isSamePendingQuest({ id: 'quest-2' }, 'quest-1'), false)
    assert.equal(Progress.isSamePendingQuest(null, 'quest-1'), false)
})
