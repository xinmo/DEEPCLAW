export async function cloneVoice(
  name: string,
  audioFile: File,
  description = ""
) {
  const form = new FormData();
  form.append("name", name);
  form.append("description", description);
  form.append("file", audioFile);

  const resp = await fetch("/api/clone", {
    method: "POST",
    body: form,
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function listVoices() {
  const resp = await fetch("/api/voices");
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function deleteVoice(voiceId: string) {
  const resp = await fetch(`/api/voices/${voiceId}`, {
    method: "DELETE",
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function startCompanion(voiceId: string): Promise<{ status: string; pid?: number }> {
  const resp = await fetch("/api/companion/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ voice_id: voiceId }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    try {
      const data = JSON.parse(text);
      throw new Error(data.detail || "Failed to start companion");
    } catch {
      throw new Error(text || "Failed to start companion");
    }
  }
  return resp.json();
}

export async function stopCompanion(): Promise<{ status: string }> {
  const resp = await fetch("/api/companion/stop", {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function getCompanionStatus() {
  const resp = await fetch("/api/companion/status");
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}
