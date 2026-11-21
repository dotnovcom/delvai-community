import { toDataURL } from 'qrcode'

export async function qrCodeDataUrl(text: string, size = 240): Promise<string> {
  return toDataURL(text, {
    width: size,
    margin: 2,
    errorCorrectionLevel: 'M',
  })
}
