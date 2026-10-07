import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { renderWithI18n } from "./test/renderWithI18n";
import { TutorComposer } from "./TutorComposer";
import { I18nProvider } from "./i18n";

const speech = vi.hoisted(() => ({
  load: vi.fn(),
  transcribe: vi.fn(),
  dispose: vi.fn(),
  start: vi.fn(),
  stop: vi.fn(),
  cancel: vi.fn(),
  resume: vi.fn(),
  close: vi.fn(),
}));

vi.mock("./speech/whistleClient", () => ({
  WhistleClient: class {
    load = speech.load;
    transcribe = speech.transcribe;
    dispose = speech.dispose;
  },
}));
vi.mock("./speech/microphoneRecording", () => ({
  startMicrophoneRecording: speech.start,
}));

beforeEach(() => {
  vi.clearAllMocks();
  speech.load.mockResolvedValue(undefined);
  speech.transcribe.mockResolvedValue("Explain gradient descent.");
  speech.stop.mockResolvedValue(new Float32Array(16000));
  speech.start.mockResolvedValue({ stop: speech.stop, cancel: speech.cancel });
  speech.resume.mockResolvedValue(undefined);
  speech.close.mockResolvedValue(undefined);
  vi.stubGlobal(
    "AudioContext",
    class {
      resume = speech.resume;
      close = speech.close;
    },
  );
});

it("loads speech only on demand and appends an editable transcript without submitting", async () => {
  const send = vi.fn().mockResolvedValue(undefined);
  renderWithI18n(<TutorComposer pending={false} onSendMessage={send} />);
  expect(speech.load).not.toHaveBeenCalled();
  const field = screen.getByRole("textbox", { name: "Tutor message" });
  await userEvent.type(field, "My question:");
  const languages = screen.getByRole("radiogroup", { name: "Speech language" });
  expect(within(languages).getByRole("radio", { name: "English" })).toBeChecked();
  await userEvent.click(within(languages).getByRole("radio", { name: "Deutsch" }));
  await userEvent.click(screen.getByRole("button", { name: "Start dictation" }));
  expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  expect(within(languages).getByRole("radio", { name: "English" })).toBeDisabled();
  expect(screen.getByText("0:00 / 0:30")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Stop dictation" }));
  await waitFor(() => expect(field).toHaveValue("My question: Explain gradient descent."));
  expect(speech.transcribe).toHaveBeenCalledWith(expect.any(Float32Array), "de");
  expect(send).not.toHaveBeenCalled();
  await userEvent.type(field, " Please.");
  await userEvent.click(screen.getByRole("button", { name: "Send message" }));
  expect(send).toHaveBeenCalledWith("My question: Explain gradient descent. Please.");
});

it("keeps the draft and reports microphone permission failures", async () => {
  speech.start.mockRejectedValue(new DOMException("denied", "NotAllowedError"));
  renderWithI18n(<TutorComposer pending={false} onSendMessage={vi.fn()} />);
  const field = screen.getByRole("textbox", { name: "Tutor message" });
  await userEvent.type(field, "Keep this");
  await userEvent.click(screen.getByRole("button", { name: "Start dictation" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Microphone access was denied");
  expect(field).toHaveValue("Keep this");
  expect(speech.close).toHaveBeenCalled();
});

it("reports empty speech and inference errors without losing typed text", async () => {
  speech.transcribe.mockResolvedValueOnce("").mockRejectedValueOnce(new Error("Invalid model"));
  renderWithI18n(<TutorComposer pending={false} onSendMessage={vi.fn()} />);
  const field = screen.getByRole("textbox", { name: "Tutor message" });
  await userEvent.type(field, "Keep this");
  for (const expected of ["No speech was recognized", "Invalid model"]) {
    await userEvent.click(screen.getByRole("button", { name: "Start dictation" }));
    await userEvent.click(screen.getByRole("button", { name: "Stop dictation" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(expected);
    expect(field).toHaveValue("Keep this");
  }
});

it("cancels recording and terminates inference when the composer unmounts", async () => {
  const { unmount } = renderWithI18n(<TutorComposer pending={false} onSendMessage={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Start dictation" }));
  unmount();
  expect(speech.cancel).toHaveBeenCalled();
  expect(speech.dispose).toHaveBeenCalled();
  expect(speech.transcribe).not.toHaveBeenCalled();
});

it("cleans up a microphone that finishes opening after unmount", async () => {
  let finishOpening!: (value: unknown) => void;
  speech.start.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finishOpening = resolve;
      }),
  );
  const { unmount } = renderWithI18n(<TutorComposer pending={false} onSendMessage={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Start dictation" }));
  unmount();
  await act(async () => finishOpening({ stop: speech.stop, cancel: speech.cancel }));
  expect(speech.cancel).toHaveBeenCalled();
});

it("reports model loading failures before requesting microphone access", async () => {
  speech.load.mockRejectedValueOnce(new Error("Whistle model: HTTP 404"));
  renderWithI18n(<TutorComposer pending={false} onSendMessage={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Start dictation" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 404");
  expect(speech.start).not.toHaveBeenCalled();
  expect(speech.dispose).toHaveBeenCalled();
});

it("cancels a pending model download before opening the microphone", async () => {
  let finish!: () => void;
  speech.load.mockImplementationOnce(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
  );
  renderWithI18n(<TutorComposer pending={false} onSendMessage={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Start dictation" }));
  await userEvent.click(screen.getByRole("button", { name: "Cancel dictation" }));
  await act(async () => finish());
  expect(speech.start).not.toHaveBeenCalled();
  expect(speech.dispose).toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Start dictation" })).toBeEnabled();
});

it("requests the microphone even if audio resume stalls and then releases it", async () => {
  vi.useFakeTimers();
  try {
    speech.resume.mockImplementationOnce(() => new Promise<void>(() => {}));
    renderWithI18n(<TutorComposer pending={false} onSendMessage={vi.fn()} />);
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Start dictation" })));
    expect(speech.start).toHaveBeenCalled();
    await act(async () => vi.advanceTimersByTimeAsync(10_000));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The browser could not start audio capture",
    );
    expect(speech.cancel).toHaveBeenCalled();
    expect(speech.start.mock.calls.at(-1)?.[2].aborted).toBe(true);
  } finally {
    vi.useRealTimers();
  }
});

it("stops and transcribes automatically after 30 seconds", async () => {
  vi.useFakeTimers();
  try {
    renderWithI18n(<TutorComposer pending={false} onSendMessage={vi.fn()} />);
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Start dictation" })));
    expect(screen.getByRole("button", { name: "Stop dictation" })).toBeEnabled();
    await act(async () => vi.advanceTimersByTimeAsync(30_000));
    expect(speech.stop).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("textbox", { name: "Tutor message" })).toHaveValue(
      "Explain gradient descent.",
    );
  } finally {
    vi.useRealTimers();
  }
});

it("discards a late transcript after a tutor turn starts", async () => {
  let finish!: (value: string) => void;
  speech.transcribe.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const send = vi.fn();
  const { rerender } = renderWithI18n(<TutorComposer pending={false} onSendMessage={send} />);
  await userEvent.click(screen.getByRole("button", { name: "Start dictation" }));
  await userEvent.click(screen.getByRole("button", { name: "Stop dictation" }));
  rerender(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <TutorComposer pending onSendMessage={send} />
    </I18nProvider>,
  );
  await act(async () => finish("Discard this"));
  expect(screen.getByRole("textbox", { name: "Tutor message" })).toHaveValue("");
  expect(speech.dispose).toHaveBeenCalled();
});
