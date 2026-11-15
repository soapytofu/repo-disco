module Kernel {
  function Endpoint(start: int, length: int, cap: int): int {
    if start + length <= cap then start + length else cap
  }
}
