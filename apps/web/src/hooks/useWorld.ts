"use client";

import { useSyncExternalStore } from "react";
import { getWorld, subscribe, type WorldState } from "@/lib/demo-store";

export function useWorld(): WorldState {
  return useSyncExternalStore(subscribe, getWorld, getWorld);
}