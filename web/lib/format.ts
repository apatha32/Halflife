/** Probability as a percent, with an extra decimal below 10%. */
export const pct = (p: number) => `${(p * 100).toFixed(p < 0.1 ? 2 : 1)}%`;
