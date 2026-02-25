import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import type { UserProfile, UserProfileUpdate } from "../types";

type ProfileContextValue = {
  profile: UserProfile;
  loading: boolean;
  error: string | null;
  refreshProfile: () => Promise<void>;
  saveProfile: (update: UserProfileUpdate) => Promise<UserProfile>;
};

const DEFAULT_PROFILE: UserProfile = {
  user_id: USER_ID,
  username: "unknown",
  channel: "web",
  platform_id: "",
  currency: "USD",
  timezone: "UTC",
  locale: "en-US",
};

const ProfileContext = createContext<ProfileContextValue | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refreshProfile() {
    try {
      const next = await api.getProfile(USER_ID);
      setProfile(next);
      setError(null);
    } catch {
      setError("Failed to load profile settings");
      setProfile((prev) => prev ?? DEFAULT_PROFILE);
    } finally {
      setLoading(false);
    }
  }

  async function saveProfile(update: UserProfileUpdate): Promise<UserProfile> {
    const updated = await api.updateProfile(USER_ID, update);
    setProfile(updated);
    setError(null);
    return updated;
  }

  useEffect(() => {
    refreshProfile();
  }, []);

  const value = useMemo(
    () => ({ profile, loading, error, refreshProfile, saveProfile }),
    [profile, loading, error]
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile() {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error("useProfile must be used inside ProfileProvider");
  }
  return context;
}
