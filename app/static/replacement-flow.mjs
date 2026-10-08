export async function replaceQuest({ questId, request, discardQuest, generateQuest, onDiscarded }) {
    await discardQuest(questId)
    onDiscarded()
    return generateQuest(request)
}
