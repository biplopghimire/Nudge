import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";

import { guessKind, pickMaterials } from "../materials";

jest.mock("expo-document-picker", () => ({ getDocumentAsync: jest.fn() }));
jest.mock("expo-image-picker", () => ({
  requestCameraPermissionsAsync: jest.fn(),
  launchCameraAsync: jest.fn(),
  launchImageLibraryAsync: jest.fn(),
}));

const documents = jest.mocked(DocumentPicker);
const images = jest.mocked(ImagePicker);

describe("guessKind", () => {
  it.each([
    ["HW3 Solutions.pdf", "other", true],
    ["answer key - quiz 2.pdf", "other", true],
    ["Grading rubric.pdf", "other", true],
    ["Syllabus Fall 2025.pdf", "syllabus", false],
    ["hw4.pdf", "homework", false],
    ["Problem Set 2.pdf", "homework", false],
    ["Lab 1 instructions.pdf", "homework", false],
    ["Lecture 05 - Limits.pdf", "slides", false],
    ["week1-slides.pdf", "slides", false],
    ["chapter 3 reading.pdf", "notes", false],
  ])("%s → %s", (name, kind, restricted) => {
    expect(guessKind(name, "application/pdf")).toEqual({ kind, restricted });
  });

  it("treats other images as photos", () => {
    expect(guessKind("IMG_0042.jpg", "image/jpeg")).toEqual({ kind: "photo", restricted: false });
  });

  it("doesn't match 'key' inside another word", () => {
    expect(guessKind("keyboard shortcuts.pdf", "application/pdf").restricted).toBe(false);
  });
});

describe("pickMaterials", () => {
  beforeEach(() => jest.clearAllMocks());

  it("returns nothing when the picker is canceled", async () => {
    documents.getDocumentAsync.mockResolvedValue({ canceled: true, assets: null });
    await expect(pickMaterials("files")).resolves.toEqual([]);
  });

  it("tags files from the Files app", async () => {
    documents.getDocumentAsync.mockResolvedValue({
      canceled: false,
      assets: [
        {
          uri: "file:///hw1.pdf",
          name: "hw1.pdf",
          size: 2048,
          mimeType: undefined,
          lastModified: 0,
        },
      ],
    });
    await expect(pickMaterials("files")).resolves.toEqual([
      {
        uri: "file:///hw1.pdf",
        name: "hw1.pdf",
        type: "application/pdf",
        size: 2048,
        kind: "homework",
        restricted: false,
      },
    ]);
  });

  it("strips the iOS photo ID from library file names", async () => {
    images.launchImageLibraryAsync.mockResolvedValue({
      canceled: false,
      assets: [
        {
          uri: "file:///shot.png",
          fileName: "Screenshot 2025-11-05 at 9.41.12 AM-70B62FA5-76AA-41FD-B35E-BB958B925F72.png",
          mimeType: "image/png",
          fileSize: 900,
          width: 10,
          height: 10,
        },
      ],
    });
    const [picked] = await pickMaterials("library");
    expect(picked.name).toBe("Screenshot 2025-11-05 at 9.41.12 AM.png");
    expect(picked.kind).toBe("photo");
  });

  it("names unnamed photos and numbers them when there are several", async () => {
    const asset = { uri: "file:///p.jpg", width: 10, height: 10 };
    images.launchImageLibraryAsync.mockResolvedValue({ canceled: false, assets: [asset, asset] });
    const picked = await pickMaterials("library");
    expect(picked.map((p) => p.name)).toEqual([
      expect.stringMatching(/^Photo .+ \(1\)\.jpg$/),
      expect.stringMatching(/^Photo .+ \(2\)\.jpg$/),
    ]);
    expect(picked[0].type).toBe("image/jpeg");
  });

  it("doesn't open the camera without permission", async () => {
    images.requestCameraPermissionsAsync.mockResolvedValue({
      granted: false,
    } as ImagePicker.CameraPermissionResponse);
    await expect(pickMaterials("camera")).resolves.toEqual([]);
    expect(images.launchCameraAsync).not.toHaveBeenCalled();
  });
});
