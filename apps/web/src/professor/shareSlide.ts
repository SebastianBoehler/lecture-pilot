import QRCode from "qrcode";

import { fitTitle, LINE_HEIGHT, wrapWords, type Measure } from "./shareSlideLayout";

/** 16:9 slide a lecturer can drop into the deck: course, three steps and the QR code. */
export type ShareSlideTexts = {
  eyebrow: string;
  steps: [string, string, string];
  scan: string;
};

export type ShareSlideInput = {
  url: string;
  title: string;
  meta: string;
  texts: ShareSlideTexts;
};

const WIDTH = 1600;
const HEIGHT = 900;
const FONT = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const COLORS = {
  background: "#fbfaf7",
  card: "#ffffff",
  border: "#d7d4cb",
  text: "#17191c",
  muted: "#5f6672",
  accent: "#0b57d0",
  onAccent: "#ffffff",
};
// The favicon's "LP" mark, drawn in its 64-unit viewBox.
const LOGO_PATHS = [
  "M17 15v34h23v-8H26V15z",
  "M34 15v20h9c8 0 13-4 13-10s-5-10-13-10zm8 7h2c3 0 4 1 4 3s-1 3-4 3h-2z",
];
const LEFT = 112;
const TEXT_WIDTH = 740;
const CARD = { x: 968, y: 154, width: 520, height: 592, padding: 52 };

export async function renderShareSlide(input: ShareSlideInput): Promise<string> {
  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Canvas is unavailable.");
  const measure: Measure = (text, size) => {
    context.font = font(size, 700);
    return context.measureText(text).width;
  };

  context.fillStyle = COLORS.background;
  context.fillRect(0, 0, WIDTH, HEIGHT);
  drawBrand(context);

  context.fillStyle = COLORS.accent;
  context.font = font(28, 600);
  context.fillText(input.texts.eyebrow, LEFT, 268);

  const title = fitTitle(measure, input.title, {
    maxWidth: TEXT_WIDTH,
    maxHeight: 236,
    maxLines: 3,
    sizes: [84, 76, 68, 60, 54],
  });
  context.fillStyle = COLORS.text;
  context.font = font(title.size, 700);
  let baseline = 268 + 28 + title.size * 0.95;
  for (const line of title.lines) {
    context.fillText(line, LEFT, baseline);
    baseline += title.size * LINE_HEIGHT;
  }
  if (input.meta) {
    context.fillStyle = COLORS.muted;
    context.font = font(28, 500);
    context.fillText(input.meta, LEFT, baseline - title.size * LINE_HEIGHT + 56);
  }

  input.texts.steps.forEach((step, index) => drawStep(context, measure, index, step));
  await drawQrCard(context, input);
  return canvas.toDataURL("image/png");
}

function drawBrand(context: CanvasRenderingContext2D) {
  context.fillStyle = COLORS.accent;
  context.beginPath();
  context.roundRect(LEFT, 96, 64, 64, 14);
  context.fill();
  context.save();
  context.translate(LEFT, 96);
  context.fillStyle = COLORS.onAccent;
  for (const path of LOGO_PATHS) context.fill(new Path2D(path));
  context.restore();
  context.fillStyle = COLORS.text;
  context.font = font(34, 700);
  context.fillText("LecturePilot", LEFT + 84, 140);
}

function drawStep(
  context: CanvasRenderingContext2D,
  measure: Measure,
  index: number,
  text: string,
) {
  const y = 640 + index * 72;
  context.fillStyle = COLORS.accent;
  context.beginPath();
  context.arc(LEFT + 22, y - 10, 22, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = COLORS.onAccent;
  context.font = font(24, 700);
  context.textAlign = "center";
  context.fillText(String(index + 1), LEFT + 22, y - 1);
  context.textAlign = "left";
  context.fillStyle = COLORS.text;
  context.font = font(30, 500);
  const [line] = wrapWords(measure, text, 30, TEXT_WIDTH - 64);
  context.fillText(line ?? "", LEFT + 64, y);
}

async function drawQrCard(context: CanvasRenderingContext2D, input: ShareSlideInput) {
  context.fillStyle = COLORS.card;
  context.strokeStyle = COLORS.border;
  context.lineWidth = 2;
  context.beginPath();
  context.roundRect(CARD.x, CARD.y, CARD.width, CARD.height, 32);
  context.fill();
  context.stroke();

  const qrSize = CARD.width - CARD.padding * 2;
  const qr = new Image();
  qr.src = await QRCode.toDataURL(input.url, {
    margin: 0,
    width: qrSize,
    errorCorrectionLevel: "M",
    color: { dark: COLORS.text, light: COLORS.card },
  });
  await qr.decode();
  context.drawImage(qr, CARD.x + CARD.padding, CARD.y + CARD.padding, qrSize, qrSize);

  const center = CARD.x + CARD.width / 2;
  context.textAlign = "center";
  context.fillStyle = COLORS.text;
  context.font = font(30, 700);
  context.fillText(input.texts.scan, center, CARD.y + CARD.padding + qrSize + 64);
  context.textAlign = "left";
}

function font(size: number, weight: number) {
  return `${weight} ${size}px ${FONT}`;
}
