export type UploadMaterialFile = File & {
  lecturePilotRelativePath?: string;
  webkitRelativePath?: string;
};

type MaterialEntry = {
  isDirectory: boolean;
  isFile: boolean;
  name: string;
};

type MaterialFileEntry = MaterialEntry & {
  file: (success: (file: File) => void, error?: (error: DOMException) => void) => void;
};

type MaterialDirectoryEntry = MaterialEntry & {
  createReader: () => {
    readEntries: (success: (entries: MaterialEntry[]) => void, error?: (error: DOMException) => void) => void;
  };
};

type DataTransferItemWithEntry = {
  webkitGetAsEntry?: () => MaterialEntry | null;
};

export async function materialFilesFromDrop(dataTransfer: DataTransfer): Promise<File[]> {
  const entries: MaterialEntry[] = [];
  for (const item of Array.from(dataTransfer.items)) {
    const entry = (item as unknown as DataTransferItemWithEntry).webkitGetAsEntry?.();
    if (entry) entries.push(entry);
  }
  if (!entries.length) return Array.from(dataTransfer.files);
  const nested = await Promise.all(entries.map((entry) => filesFromEntry(entry, "")));
  return nested.flat();
}

export function fileRelativePath(file: File) {
  const uploadFile = file as UploadMaterialFile;
  return uploadFile.lecturePilotRelativePath || uploadFile.webkitRelativePath || file.name;
}

async function filesFromEntry(entry: MaterialEntry, parentPath: string): Promise<File[]> {
  const entryPath = [parentPath, entry.name].filter(Boolean).join("/");
  if (entry.isFile) return [await fileFromEntry(entry as MaterialFileEntry, entryPath)];
  if (!entry.isDirectory) return [];
  const children = await readAllEntries(entry as MaterialDirectoryEntry);
  const nested = await Promise.all(children.map((child) => filesFromEntry(child, entryPath)));
  return nested.flat();
}

function fileFromEntry(entry: MaterialFileEntry, relativePath: string): Promise<File> {
  return new Promise((resolve, reject) => {
    entry.file((file) => {
      Object.defineProperty(file, "lecturePilotRelativePath", {
        configurable: true,
        value: relativePath,
      });
      resolve(file);
    }, reject);
  });
}

async function readAllEntries(entry: MaterialDirectoryEntry): Promise<MaterialEntry[]> {
  const reader = entry.createReader();
  const entries: MaterialEntry[] = [];
  while (true) {
    const batch = await new Promise<MaterialEntry[]>((resolve, reject) => {
      reader.readEntries(resolve, reject);
    });
    if (!batch.length) return entries;
    entries.push(...batch);
  }
}
