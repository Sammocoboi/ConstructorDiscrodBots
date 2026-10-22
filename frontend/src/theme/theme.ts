import { createTheme, type MantineColorsTuple } from '@mantine/core'
import { tokens } from './tokens'

const brand: MantineColorsTuple = [
  '#eef0ff',
  '#d9ddff',
  '#b0b8ff',
  '#858fff',
  '#646ded',
  '#4e55d8',
  '#4148c6',
  '#343aac',
  '#2a2f8e',
  '#1f2472',
]

const success: MantineColorsTuple = [
  '#e9f8ee',
  '#d2eedb',
  '#a5dcb8',
  '#74c993',
  '#4cb975',
  '#34ae61',
  '#27a955',
  '#199345',
  '#0c823a',
  '#006f2d',
]

const warning: MantineColorsTuple = [
  '#fff8e1',
  '#ffefc2',
  '#ffdd8a',
  '#ffca4f',
  '#feba24',
  '#feaf0e',
  '#faa81a',
  '#de9300',
  '#c68200',
  '#ad6f00',
]

const danger: MantineColorsTuple = [
  '#ffecee',
  '#ffd7da',
  '#f8abb1',
  '#f27c85',
  '#ed5560',
  '#ed4245',
  '#d9363e',
  '#bd2c35',
  '#a1252e',
  '#871c26',
]

export const theme = createTheme({
  primaryColor: 'brand',
  primaryShade: { light: 5, dark: 5 },
  colors: { brand, success, warning, danger },
  fontFamily: tokens.fonts.body,
  fontFamilyMonospace: tokens.fonts.mono,
  headings: {
    fontFamily: tokens.fonts.body,
    fontWeight: '700',
  },
  defaultRadius: 'md',
  cursorType: 'pointer',
  components: {
    Button: {
      defaultProps: { radius: 'md' },
      styles: { root: { fontWeight: 600 } },
    },
    Card: {
      defaultProps: { radius: 'lg', withBorder: true },
    },
    Paper: {
      defaultProps: { radius: 'lg' },
    },
    Modal: {
      defaultProps: { radius: 'lg', centered: true },
    },
    Drawer: {
      defaultProps: { radius: 'lg' },
    },
    TextInput: { defaultProps: { radius: 'md' } },
    PasswordInput: { defaultProps: { radius: 'md' } },
    Textarea: { defaultProps: { radius: 'md' } },
    Select: { defaultProps: { radius: 'md' } },
    MultiSelect: { defaultProps: { radius: 'md' } },
    NumberInput: { defaultProps: { radius: 'md' } },
    Switch: { defaultProps: { withThumbIndicator: true } },
    Badge: { defaultProps: { radius: 'sm' } },
    Tabs: { defaultProps: { keepMounted: false } },
    Tooltip: { defaultProps: { withArrow: true, openDelay: 250 } },
  },
})
