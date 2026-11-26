import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { renderWithI18n } from "../test/renderWithI18n";
import { PairedInkDialog, RecallDialog } from "./RecallDialog";
import type { RecallTarget } from "./recallTarget";

vi.mock("qrcode", () => ({
  default: { toDataURL: async () => "data:image/png;base64,qr" },
}));

const code = "abcdefghijklmnopqrstuvwxyz123456";
const target: RecallTarget = {
  courseId: "course",
  lectureId: "lecture",
  sectionId: "section",
  publicationVersion: 2,
  blockId: "section-text",
  title: "Decision boundaries",
  session: { username: "student", term: "Term", courses: [] },
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("requires a received iPad page before asking the tutor and saves only an explicit correction", async () => {
  const fetchMock = vi.fn(async (_url, init) => {
    if (init.method === "POST") return Response.json({ code, expires_in: 900 });
    if (init.method === "GET") return Response.json({ image: "handwritten-page" });
    if (init.method === "DELETE") return new Response(null, { status: 204 });
    return Response.json({ id: "saved-correction" });
  });
  vi.stubGlobal("fetch", fetchMock);
  const submit = vi.fn().mockResolvedValue("Mention the boundary condition.");
  const onSaved = vi.fn();
  const user = userEvent.setup();
  renderWithI18n(
    <RecallDialog target={target} onSubmit={submit} onClose={vi.fn()} onSaved={onSaved} />,
  );

  const dialog = screen.getByRole("dialog", { name: "Recall from this section" });
  const feedback = within(dialog).getByRole("button", { name: "Get tutor feedback" });
  expect(feedback).toBeDisabled();
  const link = await within(dialog).findByRole("link", { name: "Open handwriting link" });
  expect(link).toHaveAttribute(
    "href",
    expect.stringContaining(`/courses/course/lectures/lecture#ink=${code}`),
  );
  await within(dialog).findByRole(
    "img",
    { name: "Handwritten page received from iPad" },
    { timeout: 2000 },
  );
  expect(submit).not.toHaveBeenCalled();
  await user.click(feedback);
  expect(submit).toHaveBeenCalledExactlyOnceWith("handwritten-page");

  await user.click(within(dialog).getByText("View submitted page"));
  expect(within(dialog).getByRole("img", { name: "Your submitted recall page" })).toHaveAttribute(
    "src",
    "data:image/jpeg;base64,handwritten-page",
  );
  expect(submit).toHaveBeenCalledOnce();
  const correction = within(dialog).getByRole("textbox", {
    name: "Write one correction to remember",
  });
  const save = within(dialog).getByRole("button", { name: "Save correction" });
  expect(save).toBeDisabled();
  await user.type(correction, "State the condition explicitly.");
  await user.click(save);
  expect(
    await within(dialog).findByText("Correction saved beside the section."),
  ).toBeInTheDocument();
  const [url, init] = fetchMock.mock.lastCall!;
  expect(url).toContain("/annotations/");
  expect(JSON.parse(init.body)).toEqual({
    block_id: "section-text",
    publication_version: 2,
    comment: "State the condition explicitly.",
  });
  expect(onSaved).toHaveBeenCalledOnce();
});

it("keeps pencil strokes local until the iPad sends the finished page", async () => {
  const fetchMock = vi.fn(async () => Response.json({ received: true }));
  vi.stubGlobal("fetch", fetchMock);
  const draw = { fillRect: vi.fn(), beginPath: vi.fn(), arc: vi.fn(), fill: vi.fn() };
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
    draw as unknown as CanvasRenderingContext2D,
  );
  vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue("data:image/jpeg;base64,ink");
  const user = userEvent.setup();
  renderWithI18n(<PairedInkDialog lecture={target} code={code} onClose={vi.fn()} />);
  const canvas = screen.getByLabelText("Handwriting pad", { selector: "canvas" });
  Object.defineProperty(canvas, "setPointerCapture", { value: vi.fn() });
  vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 300, 225));
  const send = screen.getByRole("button", { name: "Send page to desktop" });
  expect(send).toBeDisabled();
  fireEvent.pointerDown(canvas, {
    pointerId: 8,
    pointerType: "touch",
    clientX: 30,
    clientY: 30,
    button: 0,
  });
  expect(send).toBeDisabled();
  fireEvent.pointerDown(canvas, {
    pointerId: 7,
    pointerType: "pen",
    clientX: 30,
    clientY: 30,
    button: 0,
  });
  fireEvent.pointerUp(canvas, { pointerId: 7, pointerType: "pen" });
  expect(draw.arc).toHaveBeenCalled();
  expect(fetchMock).not.toHaveBeenCalled();
  await user.click(send);
  expect(
    await screen.findByText("Page sent to your desktop. Get feedback there."),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining(`/ink-pair/${code}`),
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({ image: "ink" }),
    }),
  );
});
