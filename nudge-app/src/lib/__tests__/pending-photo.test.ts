import { pendingPhoto } from "../pending-photo";

const photo = { uri: "file:///photo.jpg", width: 1200, height: 900 };

describe("pendingPhoto", () => {
  it("hands the photo to the chat that opened the camera, once", () => {
    pendingPhoto.set("thread-1", photo);
    expect(pendingPhoto.take("thread-1")).toEqual(photo);
    expect(pendingPhoto.take("thread-1")).toBeNull();
  });

  it("keeps the photo away from other chats", () => {
    pendingPhoto.set("thread-1", photo);
    expect(pendingPhoto.take("thread-2")).toBeNull();
    expect(pendingPhoto.take("thread-1")).toEqual(photo);
  });
});
