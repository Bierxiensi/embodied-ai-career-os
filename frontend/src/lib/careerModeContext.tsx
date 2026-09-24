"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getCareerModeOverview } from "@/services/careerModeService";
import type { CareerMode } from "@/types";

interface CareerModeContextValue {
  /** 当前生效的模式（null = 加载中或后端不可用）。 */
  current: CareerMode | null;
  /** 可切换的全部模式。 */
  available: CareerMode[];
  /** 首次加载是否完成。 */
  isLoading: boolean;
  /** ModeSwitcher 切换成功后调用，就地更新 Context 状态。 */
  refreshMode: (newCurrent: CareerMode) => void;
}

const CareerModeContext = createContext<CareerModeContextValue>({
  current: null,
  available: [],
  isLoading: true,
  refreshMode: () => {},
});

/** 默认模式（后端不可用时的降级值）。 */
const DEFAULT_MODE: CareerMode = {
  id: "0",
  key: "job_hunt",
  name: "求职冲刺模式",
  objective: "在目标期限前获得符合条件的 Offer",
  deadline: null,
  daysLeft: null,
  activeTrackKeys: [],
  frozenTrackKeys: [],
  isCurrent: true,
};

/** CareerMode 全局状态提供者。
 *
 * 职责：
 *   - 首次挂载时从后端拉取当前模式（失败时降级为默认 job_hunt）
 *   - 提供 refreshMode() 供 ModeSwitcher 切换后就地更新
 *   - 导航组件（GlobalNav / Sidebar）通过 useCareerMode() 读取当前模式
 *
 * 为什么用 Context 而不是让每个组件自己 fetch：
 *   模式是全局状态，GlobalNav、Sidebar、ModeSwitcher 都需要它。
 *   让三个组件各自 fetch 会产生 3 次请求 + 状态不一致的窗口。
 */
export function CareerModeProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<CareerMode | null>(null);
  const [available, setAvailable] = useState<CareerMode[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    getCareerModeOverview()
      .then((data) => {
        if (cancelled) return;
        setCurrent(data.current);
        setAvailable(data.available);
      })
      .catch(() => {
        if (cancelled) return;
        // 后端不可用时降级为默认模式，导航仍能正常渲染
        setCurrent(DEFAULT_MODE);
        setAvailable([DEFAULT_MODE]);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const refreshMode = useCallback((newCurrent: CareerMode) => {
    setCurrent(newCurrent);
    setAvailable((prev) =>
      prev.map((m) => ({ ...m, isCurrent: m.key === newCurrent.key }))
    );
  }, []);

  return (
    <CareerModeContext.Provider value={{ current, available, isLoading, refreshMode }}>
      {children}
    </CareerModeContext.Provider>
  );
}

/** 读取当前 CareerMode 全局状态。 */
export function useCareerMode(): CareerModeContextValue {
  return useContext(CareerModeContext);
}
