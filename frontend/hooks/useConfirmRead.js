import { useAchievements } from './useAchievements';
import { recordPaperView } from '../services/api';

/**
 * Shared "record a confirmed read" action - used by both the Libby-style prompt
 * (ReadConfirmationModal, triggered after the in-app browser closes) and the manual
 * "I've Read This!" button on paper cards (for when the prompt doesn't fire, or the user just
 * wants to confirm directly). Either path counts the same toward milestones, the streak badge,
 * and the Visualize tab - they both just call backend/api_server.py's record_paper_view.
 */
export function useConfirmRead() {
  const { triggerAchievement } = useAchievements();

  return async (token, paperId) => {
    if (!token || !paperId) return null;
    const result = await recordPaperView(token, paperId);
    if (result && result.milestone_reached) {
      triggerAchievement(result.milestone_reached);
    }
    return result;
  };
}
