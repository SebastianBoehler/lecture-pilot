import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { apiUrl } from "./api";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";

type AssetState = {
  url: string | null;
  error: string | null;
  loading: boolean;
};

type AuthenticatedAssetProps = {
  src: string;
  session: LoginSession;
};

type AuthenticatedImageProps = AuthenticatedAssetProps & {
  alt: string;
};

type AuthenticatedVideoProps = AuthenticatedAssetProps & {
  title: string;
};

type AuthenticatedAssetLinkProps = AuthenticatedAssetProps & {
  children: ReactNode;
};

export function AuthenticatedImage({ alt, session, src }: AuthenticatedImageProps) {
  const asset = useAuthenticatedAssetUrl(src, session);
  return <img alt={alt} src={asset.url ?? undefined} title={asset.error ?? undefined} />;
}

export function AuthenticatedVideo({ session, src, title }: AuthenticatedVideoProps) {
  const asset = useAuthenticatedAssetUrl(src, session);
  return <video controls src={asset.url ?? undefined} title={asset.error ?? title} />;
}

export function AuthenticatedAssetLink({ children, session, src }: AuthenticatedAssetLinkProps) {
  const asset = useAuthenticatedAssetUrl(src, session);
  return (
    <a
      aria-disabled={asset.loading || Boolean(asset.error)}
      href={asset.url ?? undefined}
      rel="noreferrer"
      target="_blank"
    >
      {children}
    </a>
  );
}

function useAuthenticatedAssetUrl(src: string, session: LoginSession): AssetState {
  const resolvedUrl = useMemo(() => apiUrl(src), [src]);
  const authKey = [
    session.access_token ?? "",
    session.auth_transport ?? "",
    session.tenant_id ?? "",
    session.username,
    (session.roles ?? []).join(","),
  ].join("|");
  const protectedAsset = isProtectedApiAsset(resolvedUrl);
  const [asset, setAsset] = useState<AssetState>(() => ({
    url: protectedAsset ? null : resolvedUrl,
    error: null,
    loading: protectedAsset,
  }));

  useEffect(() => {
    if (!protectedAsset) {
      setAsset({ url: resolvedUrl, error: null, loading: false });
      return undefined;
    }

    let active = true;
    let objectUrl: string | null = null;
    setAsset({ url: null, error: null, loading: true });
    void fetch(resolvedUrl, authRequestInit(session))
      .then(async (response) => {
        if (!response.ok) throw new Error("Asset could not be loaded.");
        objectUrl = URL.createObjectURL(await response.blob());
        if (active) setAsset({ url: objectUrl, error: null, loading: false });
      })
      .catch(() => {
        if (active) setAsset({ url: null, error: "Asset could not be loaded.", loading: false });
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [authKey, protectedAsset, resolvedUrl, session]);

  return asset;
}

function isProtectedApiAsset(url: string) {
  const parsed = new URL(url, window.location.href);
  const apiOrigin = new URL(apiUrl("/"), window.location.href).origin;
  return (
    parsed.origin === apiOrigin &&
    (parsed.pathname.startsWith("/course-assets/") ||
      parsed.pathname.startsWith("/workspace-assets/"))
  );
}
