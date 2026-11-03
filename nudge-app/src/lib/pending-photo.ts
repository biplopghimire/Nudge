/**
 * Hand-off from the camera screen back to the chat that opened it.
 * The camera puts the photo here; the chat picks it up when it regains focus.
 */
type Photo = { uri: string; width: number; height: number };

let pending: { threadId: string; photo: Photo } | null = null;

export const pendingPhoto = {
  set(threadId: string, photo: Photo) {
    pending = { threadId, photo };
  },
  take(threadId: string): Photo | null {
    if (pending?.threadId !== threadId) return null;
    const photo = pending.photo;
    pending = null;
    return photo;
  },
};
