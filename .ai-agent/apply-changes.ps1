# Apply changes to memory-stream.ts
$path = 'C:\Users\dfhai\WorkBuddy\2026-07-14-08-01-00\agent-platform\src\server\simulation\memory\memory-stream.ts'
$c = Get-Content $path -Raw

# Add newItems field
$old = @'
  private shortTerm: SimulationMemoryItem[] = [];
  private longTerm: SimulationMemoryItem[] = [];
  private reflections: Reflection[] = [];
'@
$new = @'
  private shortTerm: SimulationMemoryItem[] = [];
  private longTerm: SimulationMemoryItem[] = [];
  private reflections: Reflection[] = [];
  private newItems: SimulationMemoryItem[] = [];
'@
$c = $c.Replace($old, $new)

# Add newItems.push and getAndClearNewItems method
$old2 = @'
    return item;
  }

  getShortTerm(): SimulationMemoryItem[] {
'@
$new2 = @'
    this.newItems.push(item);
    return item;
  }

  getAndClearNewItems(): SimulationMemoryItem[] {
    const items = [...this.newItems];
    this.newItems = [];
    return items;
  }

  getShortTerm(): SimulationMemoryItem[] {
'@
$c = $c.Replace($old2, $new2)

[System.IO.File]::WriteAllText($path, $c, [System.Text.Encoding]::UTF8)
Write-Output 'memory-stream.ts updated'
