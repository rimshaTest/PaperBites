import React, { createContext, useCallback, useContext, useRef, useState } from 'react';

/**
 * Global achievement-popup queue. Mounted once at the app root (see app/_layout.tsx) alongside
 * <AchievementOverlay/>, so triggerAchievement(milestone) works the same from any screen -
 * the Explore feed's card, the paper detail screen, or the manual "I've Read This!" button -
 * instead of each read-confirmation surface needing its own local celebration UI.
 */
const AchievementContext = createContext({ milestone: null, triggerAchievement: () => {}, dismiss: () => {} });

export function AchievementProvider({ children }) {
  const [milestone, setMilestone] = useState(null);
  const queueRef = useRef([]);

  const dismiss = useCallback(() => {
    setMilestone(queueRef.current.length ? queueRef.current.shift() : null);
  }, []);

  const triggerAchievement = useCallback((value) => {
    if (!value) return;
    setMilestone((current) => {
      if (current === null) return value;
      queueRef.current.push(value);
      return current;
    });
  }, []);

  return (
    <AchievementContext.Provider value={{ milestone, triggerAchievement, dismiss }}>
      {children}
    </AchievementContext.Provider>
  );
}

export function useAchievements() {
  return useContext(AchievementContext);
}
