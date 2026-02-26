import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import i18next from 'eslint-plugin-i18next'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  // Enforce i18n: warn on hardcoded user-facing strings in TSX/TS source.
  // Exclusions: shadcn UI wrappers (third-party), and known non-translatable attributes.
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/components/ui/**'],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': [
        'warn',
        {
          mode: 'jsx-only',
          // Attribute names whose string values are always non-translatable.
          'jsx-attributes': {
            exclude: [
              // HTML / React core
              'className', 'style', 'key', 'id', 'htmlFor', 'name', 'type', 'role',
              'aria-label', 'aria-labelledby', 'aria-describedby', 'aria-controls',
              'href', 'src', 'alt', 'target', 'rel', 'download',
              // Routing
              'path', 'to', 'from', 'exact',
              // Data / testing attributes
              'data-testid', 'data-state', 'data-side', 'data-align', 'data-value',
              // shadcn / Radix UI component props
              'variant', 'size', 'align', 'side', 'sideOffset', 'asChild', 'position',
              'value', 'defaultValue', 'placeholder', 'step', 'label', 'emptyKey',
              // Recharts — all are config keys, not user-visible text
              'dataKey', 'nameKey', 'layout', 'stroke', 'strokeDasharray', 'fill',
              'legendType', 'orientation', 'tickLine', 'axisLine',
              // Misc non-translatable
              'icon', 'format', 'unit', 'prefix', 'suffix',
              // Component-specific props
              'message', 'guruName',
            ],
          },
          // Components where literal strings are always acceptable.
          'jsx-components': {
            exclude: ['Trans', 'Icon', 'Route', 'Redirect'],
          },
        },
      ],
    },
  },
])
