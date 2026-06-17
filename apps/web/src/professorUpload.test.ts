import { describe, expect, it } from "vitest";

import { materialFilesFromDrop } from "./materialDrop";
import { uploadDestination } from "./professorUpload";

describe("professor material uploads", () => {
  it("keeps custom relative paths from dropped folders", async () => {
    const file = new File(["content"], "Lecture01-eng.tex");
    const transfer = {
      files: [],
      items: [{
        webkitGetAsEntry: () => directoryEntry("course-folder", [
          fileEntry("Lecture01-eng.tex", file),
        ]),
      }],
    } as unknown as DataTransfer;

    const [dropped] = await materialFilesFromDrop(transfer);

    expect(uploadDestination("uploads", dropped, 3)).toBe("uploads/course-folder/Lecture01-eng.tex");
  });

  it("keeps nested picker paths", () => {
    const file = new File(["content"], "Lecture02-eng.tex");
    Object.defineProperty(file, "webkitRelativePath", {
      value: "slides/week-02/Lecture02-eng.tex",
    });

    expect(uploadDestination("uploads", file, 2)).toBe("uploads/slides/week-02/Lecture02-eng.tex");
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
