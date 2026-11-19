// @vitest-environment jsdom
/**
 * Shared filter inputs (components/ui.tsx) — icon alignment regression.
 *
 * The icon must sit inside the field's start edge and stay vertically
 * centered regardless of the input height: the glyph's wrapper is a
 * stretched flex container (`inset-y-0 right-3 flex! items-center`). The
 * `!` is required because fonts.googleapis.com ships an unlayered
 * `display: inline-block` rule for `.material-symbols-outlined`, which
 * outranks Tailwind's utilities layer; without it the glyph renders at the
 * top edge (the bug fixed across the panels). The control's text is padded
 * on the icon side with physical `pr-10` so the placeholder/typed text never
 * slides under the icon (RTL and LTR alike).
 */

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { FilterSelect, SearchInput } from '../components/ui'

function icon(wrapper: HTMLElement): HTMLElement {
  const span = wrapper.querySelector('.material-symbols-outlined')
  if (!span) throw new Error('icon span not rendered inside the field wrapper')
  return span as HTMLElement
}

afterEach(() => cleanup())

describe('SearchInput', () => {
  it('centers the icon in the start edge and pads the text away from it', () => {
    const { container } = render(
      <SearchInput value="" onChange={() => {}} placeholder="جستجو…" label="جستجو" />,
    )

    // The relative wrapper owns the positioning context.
    expect(container.firstElementChild?.className).toContain('relative')

    const span = icon(container)
    expect(span.className).toContain('inset-y-0')
    expect(span.className).toContain('right-3')
    expect(span.className).toContain('flex! items-center')
    // Regression: the old stretched span rendered its glyph at the top.
    expect(span.className).not.toContain('my-auto')
    // Regression: logical start-* utilities flip on Material Symbols spans,
    // whose own stylesheet forces direction:ltr — physical offsets only.
    expect(span.className).not.toContain('start-')

    const input = screen.getByLabelText('جستجو') as HTMLInputElement
    expect(input.className).toContain('pr-10')
    expect(input.className).not.toContain('ps-10')
  })

  it('stays a working controlled search field', () => {
    let latest = ''
    render(
      <SearchInput
        value={latest}
        onChange={(next) => {
          latest = next
        }}
        placeholder="جستجو…" 
        label="جستجو"
      />,
    )
    fireEvent.change(screen.getByLabelText('جستجو'), { target: { value: 'کاربر' } })
    expect(latest).toBe('کاربر')
  })
})

describe('FilterSelect', () => {
  it('uses the same centered icon slot and logical icon-side padding', () => {
    const { container } = render(
      <FilterSelect icon="badge" label="نقش" value="" onChange={() => {}}>
        <option value="">همه</option>
      </FilterSelect>,
    )

    const span = icon(container)
    expect(span.className).toContain('inset-y-0')
    expect(span.className).toContain('right-3')
    expect(span.className).toContain('flex! items-center')
    expect(span.className).not.toContain('my-auto')
    expect(span.className).not.toContain('start-')

    const select = screen.getByLabelText('نقش') as HTMLSelectElement
    expect(select.className).toContain('pr-10')
    expect(select.className).not.toContain('ps-10')
    expect(select.value).toBe('')
  })
})
