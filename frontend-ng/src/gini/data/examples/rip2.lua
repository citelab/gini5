-- A simple RIP: distance vector over link costs, 16 = unreachable.
--
-- Two tables are involved, and only one of them forwards packets:
--   dv          this script's own view (cost, next hop, age) -- the control plane
--   route table the gRouter's forwarding table (`route show`) -- the data plane
-- route_add/route_del are the only bridge, and route_add carries no cost, so
-- marking a route 16 in dv does nothing to packets unless the entry is also
-- deleted. set_route() is the ONLY writer of a learned route, and it updates
-- both tables together, so the two can never disagree.
--
-- Link costs: each link drawn in gBuilder has a cost (1-15, default 1). The router
-- hands it over as interfaces()[i].cost, so a route learned over an interface costs
-- what the neighbour advertised PLUS that link's cost. With every cost 1 this is
-- plain hop count. interfaces() is re-read every tick, since costs can change live.
--
-- When it speaks: every tick, and ALSO once at load, whenever a link changes, and in
-- answer to a neighbour that has just started. The first tick is a whole period after
-- `cp add` (5 s unless you say otherwise), and a router that hears nothing until then
-- knows only its own LANs for that long -- on a four-router chain that was 15-20 s
-- before a ping worked, which reads as "RIP is broken" when it is only slow. Worse, a
-- router that has just (re)loaded believes the FIRST vector it hears, whatever the
-- cost, until a cheaper one arrives a tick later. A just-started router's vector is
-- all cost 0 (its own LANs and nothing else), so a neighbour that receives one
-- answers at once, and the newcomer has every neighbour's vector within a round trip.
-- What is said is unchanged: the whole vector, the same on every interface. No split
-- horizon, no poison reverse -- that is rip3's job.

INF = 16
local dv, myifaces = {}, {}

local function encode(vec) -- "net cost,net cost,..."
  local p = {}
  for net, cost in pairs(vec) do p[#p + 1] = net .. " " .. cost end
  return table.concat(p, ",")
end

local function decode(s)
  local vec = {}
  for net, cost in s:gmatch("([%d%./]+) (%d+)") do vec[net] = tonumber(cost) end
  return vec
end

local function net_of(ip) return (ip:gsub("%d+$", "0")) .. "/24" end
local function addr_of(nt) return (nt:gsub("/24$", "")) end

local function cost_of(iface) -- the link cost of one of our interfaces
  for _, itf in ipairs(myifaces) do
    if itf.iface == iface then return itf.cost or 1 end
  end
  return 1
end

-- Record a route in dv AND in the router's table. A connected LAN is the
-- router's own business (it adds/removes those routes itself), so only dv changes.
local function set_route(net, r)
  local old = dv[net]
  dv[net] = r
  if r.connected then return end
  if r.cost < INF then
    route_add(addr_of(net), "255.255.255.0", r.nexthop, r.iface)
  elseif old and old.cost < INF then
    route_del(addr_of(net), "255.255.255.0")
  end
end

local function unreachable(r) -- the same route, now at 16
  return {cost = INF, nexthop = r.nexthop, iface = r.iface, age = r.age,
          connected = r.connected}
end

local function snapshot() -- what `gpipe cp status` shows: publish() sets it
  local nets = {}
  for net in pairs(dv) do nets[#nets + 1] = net end
  table.sort(nets)
  local lines = {"RIP v1 " .. #nets}
  for _, net in ipairs(nets) do
    local r = dv[net]
    lines[#lines + 1] = string.format("N %s COST %d %s", net, r.cost,
      r.connected and "connected" or ("via " .. (r.nexthop or "?")))
  end
  publish(table.concat(lines, "\n"))
end

local function advertise() -- the whole vector, the same on every interface
  local vec = {}
  for net, r in pairs(dv) do vec[net] = r.cost end
  local msg = encode(vec)
  for _, itf in ipairs(myifaces) do send(itf.iface, msg) end
end

function init(list) -- our own LANs cost 0
  myifaces = list
  for _, itf in ipairs(list) do
    set_route(net_of(itf.ip), {cost = 0, connected = true, iface = itf.iface})
  end
  advertise() -- say so now rather than a whole tick from now
  snapshot()
end

function tick() -- advertise the whole vector, then age
  myifaces = interfaces() -- pick up link costs changed since the last tick
  advertise()
  for net, r in pairs(dv) do
    if not r.connected then
      r.age = (r.age or 0) + 1
      if r.age >= 3 and r.cost < INF then set_route(net, unreachable(r)) end -- expired
    end
  end
  snapshot()
end

function on_link_change(iface, up, cost) -- a link went down, came back, or changed cost
  myifaces = interfaces()
  for net, r in pairs(dv) do
    if r.iface == iface then
      if not up and r.cost < INF then set_route(net, unreachable(r)) -- its LAN, and routes through it
      elseif up and r.connected then r.cost = 0 end                   -- our LAN is back
    end
  end
  advertise() -- the news, good or bad, goes now rather than at the next tick
  snapshot()
end

function on_message(iface, src, data) -- a neighbour's vector arrived
  local vec = decode(data)
  local newborn = next(vec) ~= nil -- only its own LANs: it has just started
  for net, cost in pairs(vec) do
    if cost > 0 then newborn = false end
    local r = dv[net]
    if not (r and r.connected) then -- never override a connected LAN
      local newc = math.min(cost + cost_of(iface), INF)
      if (not r) or newc < r.cost or r.nexthop == src then
        set_route(net, {cost = newc, nexthop = src, iface = iface, age = 0})
      end
    end
  end
  if newborn then advertise() end -- answer now; it would otherwise wait a whole tick
  snapshot()
end
