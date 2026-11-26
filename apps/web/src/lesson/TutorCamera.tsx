import { Camera, CameraOff } from "lucide-react";
import { useI18n } from "../i18n/i18n";
import type { useTutorCamera } from "./useTutorCamera";
import "./tutor-camera.css";

type CameraState = ReturnType<typeof useTutorCamera>;

export function TutorCameraButton({
  camera,
  disabled,
}: {
  camera: CameraState;
  disabled: boolean;
}) {
  const { t } = useI18n();
  const enabled = camera.status !== "off";
  const label = t(enabled ? "camera.stop" : "camera.start");
  const Icon = enabled ? CameraOff : Camera;
  return (
    <button
      type="button"
      className="tutor-camera-toggle"
      disabled={disabled && !enabled}
      aria-label={label}
      title={label}
      onClick={() => (enabled ? camera.stop() : void camera.start())}
    >
      <Icon size={16} aria-hidden="true" />
    </button>
  );
}

export function TutorCameraPreview({
  status,
  devices,
  selected,
  start,
  setPreview,
}: Pick<CameraState, "status" | "devices" | "selected" | "start" | "setPreview">) {
  const { t } = useI18n();
  return (
    <div className="tutor-camera" hidden={status === "off"}>
      <video
        ref={setPreview}
        autoPlay
        muted
        playsInline
        aria-label={t("camera.preview")}
        hidden={status !== "active"}
      />
      {status === "active" && devices.length > 1 ? (
        <select
          aria-label={t("camera.device")}
          value={selected}
          onChange={(event) => void start(event.target.value)}
        >
          {devices.map((device, index) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label || t("camera.deviceNumber", { number: index + 1 })}
            </option>
          ))}
        </select>
      ) : null}
      <p role="status">{t(status === "opening" ? "camera.opening" : "camera.attachOnSend")}</p>
    </div>
  );
}
