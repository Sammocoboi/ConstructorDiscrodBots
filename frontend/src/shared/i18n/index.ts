import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'
import { ru } from './ru'
import { en } from './en'

export const supportedLocales = ['ru', 'en'] as const
export type SupportedLocale = (typeof supportedLocales)[number]

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      ru: { translation: ru },
      en: { translation: en },
    },
    fallbackLng: 'ru',
    supportedLngs: [...supportedLocales],
    nonExplicitSupportedLngs: true,
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'botforge.language',
      caches: ['localStorage'],
    },
    interpolation: { escapeValue: false },
  })

export function setLanguage(locale: SupportedLocale) {
  void i18n.changeLanguage(locale)
  document.documentElement.lang = locale
}

document.documentElement.lang = i18n.language.startsWith('en') ? 'en' : 'ru'

export default i18n
