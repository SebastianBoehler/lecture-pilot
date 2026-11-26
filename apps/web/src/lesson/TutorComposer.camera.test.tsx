import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { renderWithI18n } from "../test/renderWithI18n";
import { TutorComposer } from "./TutorComposer";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function track(deviceId: string) {
  return Object.assign(new EventTarget(), {
    readyState: "live",
    muted: false,
    stop: vi.fn(),
    getSettings: () => ({ deviceId }),
  });
}

function installCameras() {
  const builtIn = track("built-in");
  const external = track("external");
  const stream = (videoTrack: ReturnType<typeof track>) => ({
    getTracks: () => [videoTrack],
    getVideoTracks: () => [videoTrack],
  });
  const getUserMedia = vi
    .fn()
    .mockResolvedValueOnce(stream(builtIn))
    .mockResolvedValueOnce(stream(external));
  vi.stubGlobal(
    "navigator",
    Object.create(navigator, {
      mediaDevices: {
        value: {
          getUserMedia,
          enumerateDevices: vi.fn().mockResolvedValue([
            { kind: "videoinput", deviceId: "built-in", label: "Built-in Camera" },
            { kind: "videoinput", deviceId: "external", label: "USB Document Camera" },
          ]),
        },
      },
    }),
  );
  return { getUserMedia, builtIn, external };
}

it("switches to a USB camera and attaches a fresh frame only on Send", async () => {
  const { getUserMedia, builtIn, external } = installCameras();
  const drawImage = vi.fn();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
    drawImage,
  } as unknown as CanvasRenderingContext2D);
  const encode = vi
    .spyOn(HTMLCanvasElement.prototype, "toDataURL")
    .mockReturnValueOnce("data:image/jpeg;base64,first")
    .mockReturnValueOnce("data:image/jpeg;base64,second");
  const send = vi.fn().mockResolvedValue(undefined);
  const user = userEvent.setup();
  const { unmount } = renderWithI18n(<TutorComposer pending={false} onSendMessage={send} />);

  expect(getUserMedia).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Share desk camera" }));
  const select = await screen.findByRole("combobox", { name: "Camera" });
  await user.selectOptions(select, "external");
  const preview = await screen.findByLabelText("Desk camera preview", {
    selector: "video:not([hidden])",
  });
  Object.defineProperties(preview, {
    videoWidth: { value: 1920 },
    videoHeight: { value: 1080 },
    readyState: { value: HTMLMediaElement.HAVE_CURRENT_DATA },
  });
  expect(getUserMedia).toHaveBeenLastCalledWith(
    expect.objectContaining({
      audio: false,
      video: expect.objectContaining({ deviceId: { exact: "external" } }),
    }),
  );
  expect(builtIn.stop).toHaveBeenCalledOnce();
  expect(encode).not.toHaveBeenCalled();
  expect(send).not.toHaveBeenCalled();

  const field = screen.getByRole("textbox", { name: "Tutor message" });
  for (const frame of ["first", "second"]) {
    fireEvent.change(field, { target: { value: "Check this line" } });
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(send).toHaveBeenLastCalledWith("Check this line", { cameraFrame: frame });
  }
  expect(drawImage).toHaveBeenLastCalledWith(preview, 0, 0, 1600, 900);

  unmount();
  expect(external.stop).toHaveBeenCalledOnce();
});

it("keeps the draft when the active camera has no frame", async () => {
  const { builtIn } = installCameras();
  const send = vi.fn().mockResolvedValue(undefined);
  const user = userEvent.setup();
  renderWithI18n(
    <TutorComposer
      pending={false}
      onSendMessage={send}
      recallTarget={{
        sectionId: "section",
        title: "Section",
        publicationVersion: 1,
        courseId: "course",
        lectureId: "lecture",
        session: { username: "learner", term: "Term", courses: [] },
      }}
    />,
  );
  const recall = { name: "Recall from this section" };
  expect(screen.queryByRole("button", recall)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Recall with iPad" })).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "Share desk camera" }));
  await screen.findByRole("combobox", { name: "Camera" });
  expect(screen.getByRole("button", recall)).toBeEnabled();

  const field = screen.getByRole("textbox", { name: "Tutor message" });
  fireEvent.change(field, { target: { value: "Keep my question" } });
  await user.click(screen.getByRole("button", { name: "Send message" }));
  expect(screen.getByRole("alert")).toHaveTextContent("No camera frame is available");
  expect(field).toHaveValue("Keep my question");
  expect(send).not.toHaveBeenCalled();

  await user.click(screen.getByRole("button", { name: "Stop sharing desk camera" }));
  expect(builtIn.stop).toHaveBeenCalledOnce();
  expect(screen.queryByRole("button", recall)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Send message" }));
  expect(send).toHaveBeenCalledWith("Keep my question");
});
