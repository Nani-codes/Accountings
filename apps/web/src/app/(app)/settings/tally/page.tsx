"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getTallyStatus,
  createTallyPairing,
  disconnectTally,
  type TallyStatus,
} from "@/lib/api";

export default function TallySettingsPage() {
  const router = useRouter();
  const [status, setStatus] = useState<TallyStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [pairingUrl, setPairingUrl] = useState<string | null>(null);
  const [pairingExpires, setPairingExpires] = useState<string | null>(null);
  const [showPairing, setShowPairing] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [connecting, setConnecting] = useState(false);

  // Load initial status
  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    loadStatus();
  }, [router]);

  // Poll status every 5s while pairing code is visible
  useEffect(() => {
    if (!showPairing) return;
    const interval = setInterval(() => {
      loadStatus();
    }, 5000);
    return () => clearInterval(interval);
  }, [showPairing]);

  async function loadStatus() {
    try {
      const data = await getTallyStatus();
      setStatus(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load status");
    } finally {
      setLoading(false);
    }
  }

  async function handleConnect() {
    setConnecting(true);
    try {
      const pairing = await createTallyPairing();
      setPairingCode(pairing.code);
      setPairingUrl(pairing.download_url || null);
      setPairingExpires(pairing.expires_at);
      setShowPairing(true);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create pairing");
    } finally {
      setConnecting(false);
    }
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    try {
      await disconnectTally();
      setStatus(null);
      setShowPairing(false);
      setPairingCode(null);
      setPairingUrl(null);
      setError(null);
      await loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to disconnect");
    } finally {
      setDisconnecting(false);
    }
  }

  function copyToClipboard() {
    if (pairingCode) {
      navigator.clipboard.writeText(pairingCode);
    }
  }

  function getStatusLabel(): string {
    if (!status) return "Not connected";
    switch (status.status) {
      case "not_connected":
        return "Not connected";
      case "offline":
        return "Connector offline — open Accountings Connector on the firm PC";
      case "online":
        return "Online";
      case "tally_unreachable":
        return "Connector online, but TallyPrime XML port not reachable";
      default:
        return status.status;
    }
  }

  function getStatusColor(): string {
    if (!status) return "bg-line text-ink-muted";
    switch (status.status) {
      case "online":
        return "bg-green-100 text-green-900";
      case "offline":
      case "tally_unreachable":
        return "bg-yellow-100 text-yellow-900";
      case "not_connected":
      default:
        return "bg-line text-ink-muted";
    }
  }

  const isConnected = status?.status === "online";

  if (error && loading) {
    return <p className="text-stamp">{error}</p>;
  }

  return (
    <div className="space-y-7">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Tally Connection
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Connect your TallyPrime instance to enable automated reconciliation.
        </p>
      </header>

      {/* Status Badge */}
      <div className="rounded-panel border border-line bg-void-elevated p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
              Status
            </p>
            <p className="mt-2 text-sm text-ink">{getStatusLabel()}</p>
            {status?.device_label && (
              <p className="mt-1 text-xs text-ink-muted">
                Device: {status.device_label}
              </p>
            )}
            {status?.last_seen_at && (
              <p className="mt-1 text-xs text-ink-muted">
                Last seen: {new Date(status.last_seen_at).toLocaleString()}
              </p>
            )}
          </div>
          <div
            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${getStatusColor()}`}
          >
            {status?.status || "disconnected"}
          </div>
        </div>
      </div>

      {/* Pairing Code Display */}
      {showPairing && pairingCode && (
        <div className="rounded-panel border border-line bg-void-elevated p-6">
          <h2 className="mb-4 text-sm font-semibold text-ink">
            Connect Accountings Connector
          </h2>
          <p className="mb-4 text-sm text-ink-muted">
            Enter this code in the Accountings Connector application:
          </p>

          {/* Large Code Display */}
          <div className="mb-6 rounded-lg border-2 border-dashed border-line bg-void p-6 text-center">
            <p className="font-mono text-4xl font-bold tracking-widest text-ink">
              {pairingCode}
            </p>
            <p className="mt-2 text-xs text-ink-muted">
              Expires at {new Date(pairingExpires || "").toLocaleString()}
            </p>
          </div>

          {/* Copy Button */}
          <button
            type="button"
            onClick={copyToClipboard}
            className="btn-secondary mb-4 w-full"
          >
            Copy code
          </button>

          {/* Download Link */}
          {pairingUrl ? (
            <a
              href={pairingUrl}
              download
              className="btn-primary block w-full text-center"
            >
              Download Connector
            </a>
          ) : (
            <button
              type="button"
              disabled
              className="btn-secondary w-full opacity-50"
            >
              Download link coming soon
            </button>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {!showPairing ? (
          <button
            type="button"
            onClick={handleConnect}
            disabled={connecting}
            className="btn-primary"
          >
            {connecting ? "Creating pairing…" : "Connect Tally"}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setShowPairing(false)}
            className="btn-secondary"
          >
            Hide code
          </button>
        )}

        {isConnected && (
          <button
            type="button"
            onClick={handleDisconnect}
            disabled={disconnecting}
            className="btn-secondary"
          >
            {disconnecting ? "Disconnecting…" : "Disconnect"}
          </button>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-panel border border-stamp bg-stamp/10 p-4">
          <p className="text-sm text-stamp">{error}</p>
        </div>
      )}
    </div>
  );
}
