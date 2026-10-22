import { useMutation, useQuery, useQueryClient, type QueryKey } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { useTranslation } from 'react-i18next'
import { api } from './index'
import { errorMessage } from './errors'

export const qk = {
  dashboard: ['dashboard'] as const,
  bots: ['bots'] as const,
  bot: (botId: string) => ['bots', botId] as const,
  botGuilds: (botId: string) => ['bots', botId, 'guilds'] as const,
  botEvents: (botId: string) => ['bots', botId, 'events'] as const,
  availableGuilds: ['discord-guilds'] as const,
  modules: ['modules'] as const,
  botModules: (botId: string) => ['bots', botId, 'modules'] as const,
  botModule: (botId: string, moduleId: string) =>
    ['bots', botId, 'modules', moduleId] as const,
  commands: (botId: string) => ['bots', botId, 'commands'] as const,
  library: ['commands-library'] as const,
  flows: (botId: string) => ['bots', botId, 'flows'] as const,
  flow: (botId: string, flowId: string) => ['bots', botId, 'flows', flowId] as const,
  templates: ['templates'] as const,
  myTemplates: ['templates', 'mine'] as const,
  template: (templateId: string) => ['templates', templateId] as const,
  billing: ['billing'] as const,
  account: ['account'] as const,
  sessions: ['account', 'sessions'] as const,
  notifications: ['notifications'] as const,
  messages: ['messages'] as const,
}

export function useDashboardStats() {
  return useQuery({
    queryKey: qk.dashboard,
    queryFn: () => api.dashboard.stats(),
    refetchInterval: 20_000,
  })
}

export function useBots() {
  return useQuery({
    queryKey: qk.bots,
    queryFn: () => api.bots.list(),
    refetchInterval: 15_000,
  })
}

export function useBot(botId: string | undefined) {
  return useQuery({
    queryKey: qk.bot(botId ?? ''),
    queryFn: () => api.bots.get(botId as string),
    enabled: Boolean(botId),
    refetchInterval: 12_000,
  })
}

export function useAvailableGuilds() {
  return useQuery({
    queryKey: qk.availableGuilds,
    queryFn: () => api.bots.availableGuilds(),
  })
}

export function useBotGuilds(botId: string | undefined) {
  return useQuery({
    queryKey: qk.botGuilds(botId ?? ''),
    queryFn: () => api.bots.guilds(botId as string),
    enabled: Boolean(botId),
  })
}

export function useBotEvents(botId: string | undefined) {
  return useQuery({
    queryKey: qk.botEvents(botId ?? ''),
    queryFn: () => api.bots.events(botId as string),
    enabled: Boolean(botId),
    refetchInterval: 20_000,
  })
}

export function useModules() {
  return useQuery({ queryKey: qk.modules, queryFn: () => api.modules.list() })
}

export function useBotModules(botId: string | undefined) {
  return useQuery({
    queryKey: qk.botModules(botId ?? ''),
    queryFn: () => api.modules.forBot(botId as string),
    enabled: Boolean(botId),
  })
}

export function useBotModule(botId: string | undefined, moduleId: string | undefined) {
  return useQuery({
    queryKey: qk.botModule(botId ?? '', moduleId ?? ''),
    queryFn: () => api.modules.get(botId as string, moduleId as string),
    enabled: Boolean(botId && moduleId),
  })
}

export function useCommands(botId: string | undefined) {
  return useQuery({
    queryKey: qk.commands(botId ?? ''),
    queryFn: () => api.commands.list(botId as string),
    enabled: Boolean(botId),
  })
}

export function useCommandLibrary() {
  return useQuery({ queryKey: qk.library, queryFn: () => api.commands.library() })
}

export function useFlows(botId: string | undefined) {
  return useQuery({
    queryKey: qk.flows(botId ?? ''),
    queryFn: () => api.flows.list(botId as string),
    enabled: Boolean(botId),
  })
}

export function useFlow(botId: string | undefined, flowId: string | undefined) {
  return useQuery({
    queryKey: qk.flow(botId ?? '', flowId ?? ''),
    queryFn: () => api.flows.get(botId as string, flowId as string),
    enabled: Boolean(botId && flowId),
  })
}

export function useTemplates() {
  return useQuery({ queryKey: qk.templates, queryFn: () => api.templates.list() })
}

export function useMyTemplates() {
  return useQuery({ queryKey: qk.myTemplates, queryFn: () => api.templates.mine() })
}

export function useBilling() {
  return useQuery({ queryKey: qk.billing, queryFn: () => api.billing.overview() })
}

export function useAccount() {
  return useQuery({ queryKey: qk.account, queryFn: () => api.account.get() })
}

export function useNotifications() {
  return useQuery({
    queryKey: qk.notifications,
    queryFn: () => api.notifications.list(),
    refetchInterval: 30_000,
  })
}

export function useMessageLibrary() {
  return useQuery({ queryKey: qk.messages, queryFn: () => api.messages.list() })
}

interface ToastMutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<TData>
  successMessage?: string | ((data: TData, variables: TVariables) => string)
  errorTitle?: string
  invalidateKeys?: QueryKey[]
  onSuccess?: (data: TData, variables: TVariables) => void
}

export function useToastMutation<TData, TVariables>({
  mutationFn,
  successMessage,
  errorTitle,
  invalidateKeys,
  onSuccess,
}: ToastMutationOptions<TData, TVariables>) {
  const queryClient = useQueryClient()
  const { t } = useTranslation()
  return useMutation({
    mutationFn,
    onSuccess: async (data, variables) => {
      if (invalidateKeys?.length) {
        await Promise.all(
          invalidateKeys.map((queryKey) => queryClient.invalidateQueries({ queryKey })),
        )
      }
      if (successMessage) {
        notifications.show({
          color: 'teal',
          title: t('notifications.typeSuccess'),
          message:
            typeof successMessage === 'function'
              ? successMessage(data, variables)
              : successMessage,
        })
      }
      onSuccess?.(data, variables)
    },
    onError: (error) => {
      notifications.show({
        color: 'red',
        title: errorTitle ?? t('common.error'),
        message: errorMessage(error),
        autoClose: 7000,
      })
    },
  })
}
