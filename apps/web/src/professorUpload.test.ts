import { describe, expect, it } from "vitest";

import { materialFilesFromDrop } from "./materialDrop";
import {
  ignoredUploadNotice,
  isSkippableUploadError,
  preflightMaterialFiles,
  uploadDestination,
} from "./professorUpload";

describe("professor material uploads", () => {
  it("keeps custom relative paths from dropped folders", async () => {
    const file = new File(["content"], "Lecture01-eng.tex");
    const transfer = {
      files: [],
      items: [
        {
          webkitGetAsEntry: () =>
            directoryEntry("course-folder", [fileEntry("Lecture01-eng.tex", file)]),
        },
      ],
    } as unknown as DataTransfer;

    const [dropped] = await materialFilesFromDrop(transfer);

    expect(uploadDestination(dropped)).toBe("uploads/course-folder/Lecture01-eng.tex");
  });

  it("keeps nested picker paths", () => {
    const file = new File(["content"], "Lecture02-eng.tex");
    Object.defineProperty(file, "webkitRelativePath", {
      value: "slides/week-02/Lecture02-eng.tex",
    });

    expect(uploadDestination(file)).toBe("uploads/slides/week-02/Lecture02-eng.tex");
  });

  it("continues folder retries past files that were already uploaded", () => {
    expect(
      isSkippableUploadError(new Error("A course material file already exists at this path.")),
    ).toBe(true);
    expect(isSkippableUploadError(new Error("File type .aux is not writable."))).toBe(true);
    expect(
      isSkippableUploadError(new Error("File contents do not match the requested file type.")),
    ).toBe(true);
    expect(
      isSkippableUploadError(
        new Error("Declared media type does not match the requested file type."),
      ),
    ).toBe(true);
    expect(isSkippableUploadError(new Error("The backend is unavailable."))).toBe(false);
  });

  it("names ignored companion files without presenting the batch as failed", () => {
    expect(ignoredUploadNotice(["course/main.aux", "course/slides.log"])).toBe(
      " Ignored 2 files: main.aux, slides.log.",
    );
  });

  it("mirrors the advertised server policy before transferring folder files", () => {
    const oversized = new File(["large"], "large.pdf");
    const hidden = new File(["private"], "notes.md");
    Object.defineProperty(hidden, "webkitRelativePath", { value: ".private/notes.md" });
    const result = preflightMaterialFiles(
      [
        new File(["# Lecture"], "lecture.md"),
        new File(["build"], "lecture.aux"),
        new File([], "empty.md"),
        oversized,
        hidden,
      ],
      [
        { suffix: ".md", kind: "markdown", max_bytes: 1024 },
        { suffix: ".pdf", kind: "pdf", max_bytes: 2 },
      ],
    );

    expect(result.accepted.map((file) => file.name)).toEqual(["lecture.md"]);
    expect(result.excluded).toEqual([
      { path: "uploads/lecture.aux", reason: "unsupported" },
      { path: "uploads/empty.md", reason: "empty" },
      { path: "uploads/large.pdf", reason: "oversized" },
      { path: "uploads/.private/notes.md", reason: "unsafe_path" },
    ]);
  });
});

function fileEntry(name: string, file: File) {
  return {
    isDirectory: false,
    isFile: true,
    name,
    file: (success: (file: File) => void) => success(file),
  };
}

function directoryEntry(name: string, entries: unknown[]) {
  let read = false;
  return {
    isDirectory: true,
    isFile: false,
    name,
    createReader: () => ({
      readEntries: (success: (entries: unknown[]) => void) => {
        success(read ? [] : entries);
        read = true;
      },
    }),
  };
}
