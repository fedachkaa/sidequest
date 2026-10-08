const test = require('node:test')
const assert = require('node:assert/strict')

const progressModule = import('../app/static/progress-core.mjs')

test('provides the backend progress empty state shape', async () => {
    const Progress = await progressModule
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

test('renders exactly the six backend badge identifiers', async () => {
    const Progress = await progressModule
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

test('doomscroll escape keeps its fixed API request parameters', async () => {
    const Progress = await progressModule
    assert.deepEqual(Progress.doomscrollRequest(), {
        duration_minutes: 15,
        environment: 'anywhere',
        mode: 'surprise',
    })
})

test('generation and completion are unavailable during initialization or another mutation', async () => {
    const Progress = await progressModule
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

test('maps stable API error identifiers to accurate messages', async () => {
    const Progress = await progressModule
    assert.equal(
        Progress.errorMessage('QUEST_ENGINE_UNAVAILABLE', 'fallback'),
        'The local quest engine is unavailable right now.',
    )
    assert.equal(
        Progress.errorMessage('PERSISTENCE_UNAVAILABLE', 'fallback'),
        'The field record is unavailable right now.',
    )
    assert.equal(Progress.errorMessage('UNKNOWN', 'fallback'), 'fallback')
})

test('completion reconciliation handles every persisted quest status', async () => {
    const Progress = await progressModule
    assert.equal(Progress.completionResolution('completed'), 'completed')
    assert.equal(Progress.completionResolution('pending'), 'retry')
    assert.equal(Progress.completionResolution('superseded'), 'superseded')
    assert.equal(Progress.completionResolution('unexpected'), 'unknown')
})
