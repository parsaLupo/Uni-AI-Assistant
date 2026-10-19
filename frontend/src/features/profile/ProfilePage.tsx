/**
 * /profile — student onboarding + permitted profile fields (FR-STU-002).
 *
 * GET/PATCH /students/me/: the form edits student_number, degree_level,
 * entry_year and department (faculty is derived server-side). Department
 * options come from the public GET /departments/ read. Read-only fields
 * (GPA, term number, name, email) are server-managed. Validation messages
 * are Persian (Phase 05 acceptance) and digits are normalised from Persian
 * to ASCII before hitting the contract.
 */

import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  ErrorState,
  LoadingState,
  PageHeader,
  cardCls,
  inputCls,
} from '../../components/ui'
import { useAuth } from '../auth'
import { profilePage } from '../../i18n/fa'
import { toAsciiDigits, toPersianDigits } from '../../i18n/digits'
import { degreeLevelLabels } from '../../i18n/labels'

interface ProfileForm {
  student_number: string
  degree_level: 'BACHELOR' | 'MASTER' | 'PHD' | ''
  entry_year: string
  department_id: string
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return (
    <span role="alert" className="text-label-sm font-medium text-error">
      {message}
    </span>
  )
}

export function ProfilePage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)

  const profile = useQuery({
    queryKey: queryKeys.studentProfile(),
    queryFn: academicApi.studentProfile,
    enabled: user?.role === 'STUDENT',
  })
  const departments = useQuery({
    queryKey: ['departments', 'options'] as const,
    queryFn: () => academicApi.departments({ page_size: 100 }),
    enabled: user?.role === 'STUDENT',
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProfileForm>({
    defaultValues: {
      student_number: '',
      degree_level: '',
      entry_year: '',
      department_id: '',
    },
  })

  useEffect(() => {
    if (profile.data) {
      reset({
        student_number: profile.data.student_number ?? '',
        degree_level: profile.data.degree_level,
        entry_year: profile.data.entry_year ?? '',
        department_id: profile.data.department ? String(profile.data.department.id) : '',
      })
    }
  }, [profile.data, reset])

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => academicApi.updateStudentProfile(payload),
    onSuccess: (updated) => {
      setSaved(true)
      queryClient.setQueryData(queryKeys.studentProfile(), updated)
      void queryClient.invalidateQueries({ queryKey: queryKeys.planner() })
    },
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

  const onSubmit = handleSubmit((values) => {
    setSaved(false)
    const payload: Record<string, unknown> = {
      student_number: toAsciiDigits(values.student_number.trim()),
      degree_level: values.degree_level,
      entry_year: toAsciiDigits(values.entry_year.trim()),
      department_id: values.department_id ? Number(values.department_id) : null,
    }
    mutation.mutate(payload)
  })

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

      {!data.onboarding_complete ? (
        <div className="flex items-center gap-space-sm rounded-xl border border-[#FDE68A] bg-[#FFFBEB] p-space-md text-body-sm text-[#92400E]">
          <span className="material-symbols-outlined text-[20px]">info</span>
          {profilePage.onboardingNotice}
        </div>
      ) : null}
      {saved ? (
        <div
          role="status"
          className="flex items-center gap-space-sm rounded-xl border border-[#99F6E4] bg-[#F0FDFA] p-space-md text-body-sm text-[#0D9488]"
        >
          <span className="material-symbols-outlined text-[20px]">check_circle</span>
          {profilePage.saved}
        </div>
      ) : null}
      {mutation.isError ? (
        <ErrorState error={mutation.error} onRetry={() => mutation.reset()} />
      ) : null}

      <div className="grid grid-cols-1 gap-space-md lg:grid-cols-12">
        {/* Editable fields */}
        <section className={`${cardCls} p-space-lg lg:col-span-7`}>
          <h2 className="m-0 mb-space-md text-headline-md font-bold text-on-surface">
            {profilePage.edit}
          </h2>
          <form onSubmit={onSubmit} noValidate className="flex flex-col gap-space-md">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{profilePage.studentNumber}</span>
              <input
                className={inputCls}
                dir="ltr"
                inputMode="numeric"
                {...register('student_number', {
                  required: profilePage.required,
                  pattern: { value: /^[0-9]+$/, message: profilePage.required },
                })}
              />
              <FieldError message={errors.student_number?.message} />
            </label>

            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{profilePage.department}</span>
              <select
                className={inputCls}
                {...register('department_id', { required: profilePage.required })}
              >
                <option value="">{profilePage.notAvailable}</option>
                {(departments.data?.results ?? []).map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
              <FieldError message={errors.department_id?.message} />
            </label>

            <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
              <label className="flex flex-col gap-space-xs text-body-sm">
                <span className="font-semibold text-on-surface">{profilePage.degreeLevel}</span>
                <select className={inputCls} {...register('degree_level')}>
                  <option value="">{profilePage.notAvailable}</option>
                  {(['BACHELOR', 'MASTER', 'PHD'] as const).map((level) => (
                    <option key={level} value={level}>
                      {degreeLevelLabels[level]}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex flex-col gap-space-xs text-body-sm">
                <span className="font-semibold text-on-surface">{profilePage.entryYear}</span>
                <input
                  className={inputCls}
                  dir="ltr"
                  inputMode="numeric"
                  placeholder="۱۴۰۲"
                  {...register('entry_year', {
                    pattern: { value: /^[0-9]{4}$/, message: profilePage.invalidYear },
                  })}
                />
                <FieldError message={errors.entry_year?.message} />
              </label>
            </div>

            <div className="flex items-center gap-space-sm pt-space-xs">
              <button type="submit" className="rounded bg-primary-container px-space-lg py-space-sm text-label-lg font-semibold text-on-primary shadow-sm transition-all hover:bg-[#2563EB] active:scale-[0.99] disabled:opacity-75" disabled={isSubmitting || mutation.isPending}>
                {profilePage.save}
              </button>
            </div>
          </form>
        </section>

        {/* Read-only facts */}
        <section className={`${cardCls} p-space-lg lg:col-span-5`}>
          <h2 className="m-0 mb-space-sm text-headline-md font-bold text-on-surface">
            {profilePage.subtitle}
          </h2>
          <dl className="m-0 flex flex-col gap-space-sm text-body-sm">
            <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
              <dt className="text-on-surface-variant">{profilePage.studentNumber} (حساب)</dt>
              <dd className="m-0 font-semibold text-on-surface" dir="ltr">
                {data.user.email}
              </dd>
            </div>
            <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
              <dt className="text-on-surface-variant">{profilePage.faculty}</dt>
              <dd className="m-0 font-semibold text-on-surface">
                {data.faculty?.name ?? profilePage.notAvailable}
              </dd>
            </div>
            <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
              <dt className="text-on-surface-variant">{profilePage.currentGpa}</dt>
              <dd className="m-0 font-semibold text-on-surface tnum">
                {data.current_gpa ? toPersianDigits(data.current_gpa) : profilePage.notAvailable}
              </dd>
            </div>
            <div className="flex justify-between gap-space-sm">
              <dt className="text-on-surface-variant">{profilePage.currentTermNumber}</dt>
              <dd className="m-0 font-semibold text-on-surface tnum">
                {data.current_term_number
                  ? toPersianDigits(data.current_term_number)
                  : profilePage.notAvailable}
              </dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  )
}