export const formatPricingSummary = (pricing: any): string[] => {
  if (!pricing || typeof pricing !== "object") {
    return ["未配置"];
  }

  if (pricing.mode === "free") {
    return ["免费"];
  }

  if (pricing.mode === "token_segments") {
    const lines: string[] = [];
    if (pricing.input_per_million != null) {
      lines.push(`输入 $${pricing.input_per_million}/1M`);
    }
    if (pricing.cached_input_per_million != null) {
      lines.push(`缓存输入 $${pricing.cached_input_per_million}/1M`);
    }
    if (pricing.output_per_million != null) {
      lines.push(`输出 $${pricing.output_per_million}/1M`);
    }
    if (pricing.audio_input_per_million != null) {
      lines.push(`音频输入 $${pricing.audio_input_per_million}/1M`);
    }
    if (pricing.audio_output_per_million != null) {
      lines.push(`音频输出 $${pricing.audio_output_per_million}/1M`);
    }
    if (pricing.image_output_per_million != null) {
      lines.push(`图片输出 $${pricing.image_output_per_million}/1M`);
    }
    if (pricing.cache_write_5m_per_million != null) {
      lines.push(`5m 缓存写入 $${pricing.cache_write_5m_per_million}/1M`);
    }
    if (pricing.cache_write_1h_per_million != null) {
      lines.push(`1h 缓存写入 $${pricing.cache_write_1h_per_million}/1M`);
    }
    if (pricing.priority_input_per_million != null) {
      lines.push(`Priority 输入 $${pricing.priority_input_per_million}/1M`);
    }
    if (pricing.priority_output_per_million != null) {
      lines.push(`Priority 输出 $${pricing.priority_output_per_million}/1M`);
    }
    if (pricing.priority_image_output_per_million != null) {
      lines.push(`Priority 图片输出 $${pricing.priority_image_output_per_million}/1M`);
    }
    if (pricing.image_prices && typeof pricing.image_prices === "object") {
      for (const [quality, price] of Object.entries(pricing.image_prices)) {
        lines.push(`${quality} 图 $${price}/张`);
      }
    }
    if (Array.isArray(pricing.tiers) && pricing.tiers.length) {
      lines.push(`分段计费 ${pricing.tiers.length} 档`);
    }
    return lines.length ? lines : ["结构化 token 计费"];
  }

  if (pricing.unit && pricing.price != null) {
    return [`$${pricing.price}/${pricing.unit}`];
  }

  return [JSON.stringify(pricing)];
};
