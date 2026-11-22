/** 社区版只有电脑端，不跳转到 H5。 */
export function redirectPcToH5(
  _config: Record<string, string | undefined>,
  _fullPath: string,
) {
  return false
}
