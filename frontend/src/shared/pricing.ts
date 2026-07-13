type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

export const formatPricingSummary = (pricing: any, translate?: TranslateFn): string[] => {
  const t = (key: string, zh: string, params?: Record<string, string | number>): string =>
    translate ? translate(key, params) : zh;

  if (!pricing || typeof pricing !== "object") {
    return [t("pricing.notConfigured", "未配置")];
  }

  // Support for per_token and per_request from the issue description
  if (pricing.type === "per_token") {
    const lines: string[] = [];
    if (pricing.prompt_token_price) {
      const price = `$${pricing.prompt_token_price}`;
      lines.push(t("pricing.prompt", `Prompt: $${pricing.prompt_token_price}/1k`, { price }));
    }
    if (pricing.completion_token_price) {
      const price = `$${pricing.completion_token_price}`;
      lines.push(t("pricing.completion", `Completion: $${pricing.completion_token_price}/1k`, { price }));
    }
    return lines;
  } else if (pricing.type === "per_request") {
    const price = `$${pricing.request_price}`;
    return [t("pricing.perRequest", `$${pricing.request_price}/req`, { price })];
  }

  if (pricing.mode === "free") {
    return [t("pricing.free", "免费")];
  }

  if (pricing.mode === "token_segments") {
    const lines: string[] = [];
    const add = (key: string, amount: number | null | undefined, zhTemplate: (amount: number) => string) => {
      if (amount != null) {
        const price = `$${amount}`;
        lines.push(t(key, zhTemplate(amount), { price }));
      }
    };
    add("pricing.input", pricing.input_per_million, (a) => `输入 $${a}/1M`);
    add("pricing.cachedInput", pricing.cached_input_per_million, (a) => `缓存输入 $${a}/1M`);
    add("pricing.output", pricing.output_per_million, (a) => `输出 $${a}/1M`);
    add("pricing.audioInput", pricing.audio_input_per_million, (a) => `音频输入 $${a}/1M`);
    add("pricing.audioOutput", pricing.audio_output_per_million, (a) => `音频输出 $${a}/1M`);
    add("pricing.imageOutput", pricing.image_output_per_million, (a) => `图片输出 $${a}/1M`);
    add("pricing.cacheWrite5m", pricing.cache_write_5m_per_million, (a) => `5m 缓存写入 $${a}/1M`);
    add("pricing.cacheWrite1h", pricing.cache_write_1h_per_million, (a) => `1h 缓存写入 $${a}/1M`);
    add("pricing.priorityInput", pricing.priority_input_per_million, (a) => `Priority 输入 $${a}/1M`);
    add("pricing.priorityOutput", pricing.priority_output_per_million, (a) => `Priority 输出 $${a}/1M`);
    add("pricing.priorityImageOutput", pricing.priority_image_output_per_million, (a) => `Priority 图片输出 $${a}/1M`);
    if (pricing.image_prices && typeof pricing.image_prices === "object") {
      for (const [quality, price] of Object.entries(pricing.image_prices)) {
        lines.push(t("pricing.imageQuality", `${quality} 图 $${price}/张`, { quality, price: `$${price}` }));
      }
    }
    if (Array.isArray(pricing.tiers) && pricing.tiers.length) {
      lines.push(t("pricing.tierCount", `分段计费 ${pricing.tiers.length} 档`, { count: pricing.tiers.length }));
    }
    return lines.length ? lines : [t("pricing.structured", "结构化 token 计费")];
  }

  if (pricing.unit && pricing.price != null) {
    const price = `$${pricing.price}`;
    return [t("pricing.unitPrice", `$${pricing.price}/${pricing.unit}`, { price, unit: pricing.unit })];
  }

  return [JSON.stringify(pricing)];
};
