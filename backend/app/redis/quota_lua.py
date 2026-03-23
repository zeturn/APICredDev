LUA_SCRIPT = """
local delta = tonumber(ARGV[1])
local limit_minute = tonumber(ARGV[2])
local limit_hour = tonumber(ARGV[3])
local limit_day = tonumber(ARGV[4])
local limit_month = tonumber(ARGV[5])
local ttl_minute = tonumber(ARGV[6])
local ttl_hour = tonumber(ARGV[7])
local ttl_day = tonumber(ARGV[8])
local ttl_month = tonumber(ARGV[9])

local function check_and_get(key, limit)
  if not key or key == "" then
    return 0
  end
  local current = tonumber(redis.call("GET", key) or "0")
  if limit ~= -1 and current + delta > limit then
    return -1
  end
  return current
end

local keys = {KEYS[1], KEYS[2], KEYS[3], KEYS[4]}
local limits = {limit_minute, limit_hour, limit_day, limit_month}
local ttls = {ttl_minute, ttl_hour, ttl_day, ttl_month}

for i = 1, 4 do
  if keys[i] and keys[i] ~= "" then
    local res = check_and_get(keys[i], limits[i])
    if res == -1 then
      return 0
    end
  end
end

for i = 1, 4 do
  if keys[i] and keys[i] ~= "" then
    redis.call("INCRBY", keys[i], delta)
    if ttls[i] and ttls[i] > 0 then
      redis.call("EXPIRE", keys[i], ttls[i])
    end
  end
end

return 1
"""

