import type {
  ChannelListResponse,
  QQChannelConfigPayload,
  QQChannelDetail,
} from "../types/channel";

const API_BASE = "/api/channels";

async function expectJson<T>(response: Response, errorMessage: string): Promise<T> {
  if (!response.ok) {
    throw new Error(errorMessage);
  }
  return response.json() as Promise<T>;
}

export const channelApi = {
  async listChannels(): Promise<ChannelListResponse> {
    const response = await fetch(API_BASE);
    return expectJson<ChannelListResponse>(response, "加载渠道列表失败");
  },

  async getQQChannel(): Promise<QQChannelDetail> {
    const response = await fetch(`${API_BASE}/qq`);
    return expectJson<QQChannelDetail>(response, "加载 QQ 渠道配置失败");
  },

  async updateQQChannel(payload: QQChannelConfigPayload): Promise<QQChannelDetail> {
    const response = await fetch(`${API_BASE}/qq`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return expectJson<QQChannelDetail>(response, "保存 QQ 渠道配置失败");
  },
};
