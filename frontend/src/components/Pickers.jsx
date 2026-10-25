import { useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";

// options: [{ value, label, hint }]
function Picker({ options, isSelected, onPick, triggerLabel, placeholder, disabled, testId, closeOnPick }) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button type="button" variant="outline" role="combobox" disabled={disabled} className="w-full justify-between font-normal" data-testid={testId}>
          <span className="truncate">{triggerLabel}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command>
          <CommandInput placeholder={placeholder} data-testid={`${testId}-search`} />
          <CommandList>
            <CommandEmpty>Nessun risultato</CommandEmpty>
            <CommandGroup>
              {options.map((o) => (
                <CommandItem key={o.value} value={`${o.label} ${o.value}`} data-testid={`${testId}-option-${o.value}`}
                  onSelect={() => { onPick(o.value); if (closeOnPick) setOpen(false); }}>
                  <Check className={`mr-2 h-4 w-4 ${isSelected(o.value) ? "opacity-100" : "opacity-0"}`} />
                  <span className="flex-1 truncate">{o.label}</span>
                  {o.hint && <span className="ml-2 text-xs text-ink-muted">{o.hint}</span>}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export function SearchSelect({ options, value, onChange, placeholder = "Seleziona", searchPlaceholder = "Cerca per nome…", disabled, testId }) {
  const sel = options.find((o) => o.value === value);
  return (
    <Picker options={options} isSelected={(v) => v === value} onPick={onChange} closeOnPick disabled={disabled} testId={testId}
      triggerLabel={sel ? `${sel.label}${sel.hint ? ` · ${sel.hint}` : ""}` : placeholder} placeholder={searchPlaceholder} />
  );
}

export function MultiSelect({ options, selected, onToggle, placeholder = "Seleziona", searchPlaceholder = "Cerca…", testId }) {
  const labels = options.filter((o) => selected.includes(o.value)).map((o) => o.label);
  return (
    <Picker options={options} isSelected={(v) => selected.includes(v)} onPick={onToggle} testId={testId}
      triggerLabel={labels.length ? labels.join(", ") : placeholder} placeholder={searchPlaceholder} />
  );
}
