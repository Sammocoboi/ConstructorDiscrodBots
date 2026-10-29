import { Suspense, lazy, type ReactNode } from 'react'
import { MantineProvider, Center, Loader } from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import { Notifications } from '@mantine/notifications'
import { Navigate, Route, Routes } from 'react-router-dom'
import { theme } from './theme/theme'
import { useThemeStore } from './shared/stores/themeStore'
import { ErrorBoundary } from './shared/components/ErrorBoundary'
import { ProtectedRoute } from './shared/components/ProtectedRoute'
import { ScrollToTop } from './shared/components/ScrollToTop'
import { LandingPage } from './features/landing/LandingPage'
import { LoginPage } from './features/auth/LoginPage'
import { RegisterPage } from './features/auth/RegisterPage'
import { ForgotPasswordPage } from './features/auth/ForgotPasswordPage'
import { ResetPasswordPage } from './features/auth/ResetPasswordPage'
import { VerifyEmailPage } from './features/auth/VerifyEmailPage'
import { OAuthCallbackPage } from './features/auth/OAuthCallbackPage'
import { AuthLayout } from './layouts/AuthLayout'
import { AppLayout } from './layouts/AppLayout'
import { BotLayout } from './layouts/BotLayout'

const DashboardPage = lazy(() => import('./features/dashboard/DashboardPage'))
const CreateBotPage = lazy(() => import('./features/bots/CreateBotPage'))
const BotOverviewPage = lazy(() => import('./features/bots/BotOverviewPage'))
const BotStatusPage = lazy(() => import('./features/bots/BotStatusPage'))
const BotProfilePage = lazy(() => import('./features/bots/BotProfilePage'))
const BotGuildsPage = lazy(() => import('./features/bots/BotGuildsPage'))
const ModulesPage = lazy(() => import('./features/modules/ModulesPage'))
const ModuleDetailPage = lazy(() => import('./features/modules/ModuleDetailPage'))
const CommandsPage = lazy(() => import('./features/commands/CommandsPage'))
const CommandLibraryPage = lazy(() => import('./features/commands/CommandLibraryPage'))
const TemplatesPage = lazy(() => import('./features/templates/TemplatesPage'))
const MyTemplatesPage = lazy(() => import('./features/templates/MyTemplatesPage'))
const BillingPage = lazy(() => import('./features/billing/BillingPage'))
const AccountPage = lazy(() => import('./features/account/AccountPage'))
const NotificationsPage = lazy(() => import('./features/notifications/NotificationsPage'))
const HelpPage = lazy(() => import('./features/help/HelpPage'))
const NotFoundPage = lazy(() => import('./features/NotFoundPage'))

function ThemeRoot({ children }: { children: ReactNode }) {
  const preference = useThemeStore((state) => state.preference)
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
  const scheme = preference === 'auto' ? (prefersDark ? 'dark' : 'light') : preference

  return (
    <MantineProvider theme={theme} forceColorScheme={scheme}>
      {children}
    </MantineProvider>
  )
}

function RouteFallback() {
  return (
    <Center mih="60vh">
      <Loader />
    </Center>
  )
}

function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />

        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
        </Route>
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />
        <Route path="/auth/callback/discord" element={<OAuthCallbackPage />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="bots/new" element={<CreateBotPage />} />
            <Route path="bots/:botId" element={<BotLayout />}>
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="overview" element={<BotOverviewPage />} />
              <Route path="status" element={<BotStatusPage />} />
              <Route path="profile" element={<BotProfilePage />} />
              <Route path="guilds" element={<BotGuildsPage />} />
              <Route path="modules" element={<ModulesPage />} />
              <Route path="modules/:moduleId" element={<ModuleDetailPage />} />
              <Route path="commands" element={<CommandsPage />} />
              <Route path="commands/library" element={<CommandLibraryPage />} />
            </Route>
            <Route path="templates" element={<TemplatesPage />} />
            <Route path="templates/mine" element={<MyTemplatesPage />} />
            <Route path="billing" element={<BillingPage />} />
            <Route path="account" element={<AccountPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="help" element={<HelpPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeRoot>
        <ScrollToTop />
        <Notifications position="top-right" limit={4} />
        <AppRoutes />
      </ThemeRoot>
    </ErrorBoundary>
  )
}
