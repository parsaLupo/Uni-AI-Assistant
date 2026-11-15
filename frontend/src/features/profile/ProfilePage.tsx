/**
 * /profile — student academic profile (FR-STU-002, profile-improvement Part 1).
 *
 * All academic identity fields (student number, major, faculty, degree level,
 * entry year, term number, GPA) are **registrar-owned**: rendered read-only,
 * and the backend rejects direct PATCH attempts from students with 403. The
 * only permitted self change is the password (POST /auth/password-change/),
 * which re-authenticates with the current password first.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  ErrorState,
  FieldError,
  LoadingState,
  PageHeader,
  btnPrimaryCls,
  cardCls,
  inputCls,
} from '../../components/ui'
import { changePassword, useAuth } from '../auth'
import { profilePage } from '../../i18n/fa'
import { toPersianDigits } from '../../i18n/digits'
import { degreeLevelLabels } from '../../i18n/labels'
import type { DegreeLevel } from '../../types/academic'

function FactRow({ label, value, ltr = false }: { label: string; value: string; ltr?: boolean }) {
  return (
    <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
      <dt className="text-on-surface-variant">{label}</dt>
      <dd className="m-0 font-semibold text-on-surface" dir={ltr ? 'ltr' : undefined}>
        {value}
      </dd>
    </div>
  )
}

export function ProfilePage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const profile = useQuery({
    queryKey: queryKeys.studentProfile(),
    queryFn: academicApi.studentProfile,
    enabled: user?.role === 'STUDENT',
  })

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({})
  const [passwordChanged, setPasswordChanged] = useState(false)

  const change = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setPasswordChanged(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordErrors({})
      // The change revokes the refresh family server-side; refresh session
      // state so the next navigation re-authenticates cleanly.
      void queryClient.invalidateQueries({ queryKey: queryKeys.me })
    },
    onError: () => setPasswordErrors({}),
  })

  if (user?.role !== 'STUDENT') {
    return (
      <div className="px-gutter-desktop pt-space-lg">
        <ErrorState error={new Error('این بخش ویژه دانشجویان است.')} />
      </div>
    )
  }

  if (profile.isPending) {
    return (
      <div className="px-gutter-desktop pt-space-lg">
        <LoadingState />
      </div>
    )
  }
  if (profile.isError) {
    return (
      <div className="px-gutter-desktop pt-space-lg">
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </div>
    )
  }

  const data = profile.data

  const submitPassword = () => {
    setPasswordChanged(false)
    const errors: Record<string, string> = {}
    if (!currentPassword) errors.currentPassword = profilePage.required
    if (newPassword.length < 8) errors.newPassword = profilePage.passwordShort
    if (newPassword !== confirmPassword) errors.confirmPassword = profilePage.passwordMismatch
    setPasswordErrors(errors)
    if (Object.keys(errors).length > 0) return
    change.mutate()
  }

  const degreeLabel = degreeLevelLabels[data.degree_level as DegreeLevel] ?? profilePage.notAvailable

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={profilePage.title}
        subtitle={profilePage.subtitle}
        actions={
          <Chip tone="primary">
            {data.user.first_name} {data.user.last_name}
          </Chip>
        }
      />

      <div className="flex items-center gap-space-sm rounded-xl border border-outline-variant bg-surface-container p-space-md text-body-sm text-on-surface-variant">
        <span className="material-symbols-outlined text-[20px]">lock</span>
        {profilePage.readOnlyNotice}
      </div>
      {!data.onboarding_complete ? (
        <div className="flex items-center gap-space-sm rounded-xl border border-[#FDE68A] bg-[#FFFBEB] p-space-md text-body-sm text-[#92400E]">
          <span className="material-symbols-outlined text-[20px]">info</span>
          {profilePage.incompleteNotice}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-space-md lg:grid-cols-12">
        {/* Read-only academic identity (registrar-owned) */}
        <section className={`${cardCls} p-space-lg lg:col-span-7`}>
          <h2 className="m-0 mb-space-sm text-headline-md font-bold text-on-surface">
            {profilePage.subtitle}
          </h2>
          <dl className="m-0 flex flex-col gap-space-sm text-body-sm">
            <FactRow
              label={profilePage.studentNumber}
              value={data.student_number ? toPersianDigits(data.student_number) : profilePage.notAvailable}
              ltr
            />
            <FactRow label={profilePage.department} value={data.department?.name ?? profilePage.notAvailable} />
            <FactRow label={profilePage.faculty} value={data.faculty?.name ?? profilePage.notAvailable} />
            <FactRow label={profilePage.degreeLevel} value={degreeLabel} />
            <FactRow
              label={profilePage.entryYear}
              value={data.entry_year ? toPersianDigits(data.entry_year) : profilePage.notAvailable}
            />
            <FactRow
              label={profilePage.currentTermNumber}
              value={
                data.current_term_number
                  ? toPersianDigits(data.current_term_number)
                  : profilePage.notAvailable
              }
            />
            <FactRow
              label={profilePage.currentGpa}
              value={data.current_gpa ? toPersianDigits(data.current_gpa) : profilePage.notAvailable}
            />
            <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
              <dt className="text-on-surface-variant">ایمیل حساب</dt>
              <dd className="m-0 font-semibold text-on-surface" dir="ltr">
                {data.user.email}
              </dd>
            </div>
          </dl>
        </section>

        {/* Password change — the student's only self-service edit */}
        <section className={`${cardCls} p-space-lg lg:col-span-5`}>
          <h2 className="m-0 mb-space-sm text-headline-md font-bold text-on-surface">
            {profilePage.changePasswordTitle}
          </h2>
          <p className="mt-0 text-label-md text-on-surface-variant">{profilePage.changePasswordHint}</p>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              submitPassword()
            }}
            noValidate
            className="flex flex-col gap-space-md"
          >
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{profilePage.currentPassword}</span>
              <input
                type="password"
                dir="ltr"
                className={inputCls}
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                autoComplete="current-password"
              />
              <FieldError message={passwordErrors.currentPassword} />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{profilePage.newPassword}</span>
              <input
                type="password"
                dir="ltr"
                className={inputCls}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                autoComplete="new-password"
              />
              <FieldError message={passwordErrors.newPassword} />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{profilePage.confirmNewPassword}</span>
              <input
                type="password"
                dir="ltr"
                className={inputCls}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
              />
              <FieldError message={passwordErrors.confirmPassword} />
            </label>

            {passwordChanged ? (
              <div
                role="status"
                className="flex items-center gap-space-sm rounded-xl border border-[#99F6E4] bg-[#F0FDFA] p-space-md text-body-sm text-[#0D9488]"
              >
                <span className="material-symbols-outlined text-[20px]">check_circle</span>
                {profilePage.passwordChanged}
              </div>
            ) : null}
            {change.isError ? (
              <ErrorState error={change.error} onRetry={() => change.reset()} />
            ) : null}

            <div className="flex items-center gap-space-sm pt-space-xs">
              <button
                type="submit"
                className={btnPrimaryCls}
                disabled={change.isPending}
              >
                {profilePage.changePasswordTitle}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  )
}
