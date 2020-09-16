#!/usr/bin/env lua

ICON_HOME = "data/base/graphics/icons"
LOCALE_HOME = "data/base/locale/zh-CN"
RECIPE_HOME = "data/base/prototypes/recipe"


function printf(...)
    print(string.format(...))
end

--DEBUG_LOG = true

function log(...)
    if DEBUG_LOG then
        print("[DEBUG] " .. string.format(...))
	end
end

function toint(n)
    local a, b = math.modf(n)
    if b >= 0 then
        if b < 0.1 then
            return a, true
        elseif b > 0.9 then
            return a + 1, true
        else
            return a, false
        end
    else
        if b > -0.1 then
            return a, true
        elseif b < -0.9 then
            return a - 1, true
        else
            return a, false
        end
    end
end

function string.split(str, delimiter)
	if str == nil or str == '' or delimiter == nil then
		return nil
	end
	
    local ret = {}
    for match in (str .. delimiter):gmatch("(.-)" .. delimiter) do
        table.insert(ret, match)
    end
    return ret
end

function table.copy(st)
    local tab = {}
    st = st or {}
    for k, v in pairs(st) do
        if type(v) ~= "table" then
            tab[k] = v
        else
            tab[k] = table.copy(v)
        end
    end
    setmetatable(tab, getmetatable(st))
    return tab
end

-- 获取变量内容
-- example: print(vardump(data, "data"))
-- var:     var to dump
-- prefix:  name of var
-- dumped:  do not use it
-- 获取变量内容
-- example: print(vardump(data, "data"))
-- var:     var to dump
-- prefix:  name of var
-- dumped:  do not use it
function vardump(var, prefix, dumped)
    local res = ""
    if not dumped then
        dumped = {}
    end
    local t = type(var)
    if t == "table" then
        dumped[var] = prefix
        for k, v in pairs(var) do
            local tk = type(k)
            local pre
            if tk == "string" then
                pre = "." .. k
            else
                pre = "[" .. tostring(k) .. "]"
            end
            if res ~= "" then
                res = res .. "\n"
            end
            if not dumped[v] then
                res = res .. vardump(v, prefix .. pre, dumped)
            else
                res = res .. prefix .. pre .. " = " .. dumped[v] .. ""
            end
        end
        if res == "" then
            res = prefix .. " = {}"
        end
    elseif t == "number" or t == "boolean" then
        res = prefix .. " = " .. tostring(var)
    elseif t == "string" then
        res = prefix .. " = \"" .. var .. "\""
    else
        res = prefix .. " = <" .. tostring(var) .. ">"
    end

    return res
end

function readLangCfg(filename)
    local ignore = string.byte("[")
    local ret = {}
    local subMap
    for line in io.lines(filename) do
        if #line > 0 then
            if line:byte() == ignore then
                local curKey = line:sub(2, #line - 1)
                if curKey == "entity-name" or curKey == "equipment-name" or curKey == "fluid-name" or curKey == "item-name" or curKey == "recipe-name" then
                    curKey = "name"
                end
                if not ret[curKey] then
                    ret[curKey] = {}
                end
                subMap = ret[curKey]
            else
                local ss = line:split("=")
                subMap[ss[1]] = ss[2]
            end
        end
    end
    return ret
end

data = {
    var = "",
    recipes = {},
    map = {},
    idx = {}  -- result索引
}

function data:extend(t)
    log("File: " .. self.var .. ".lua")
    if not self.recipes[self.var] then
        self.recipes[self.var] = {}
    end
    for k, v in pairs(t) do
	    log("    Name: " .. v.name)
        self.recipes[self.var][k] = v
        self.map[v.name] = v

        -- 建立运算索引
        local machine = {
            output = {},
            time = v.energy_required or 0.5,
            input = {}
        }

        if v.results then
            for kk, vv in ipairs(v.results) do
                if not vv.name then
                    machine.output[vv[1]] = vv[2]
                else
                    machine.output[vv.name] = vv.amount * (vv.probability or 1.0)
                end
            end
        elseif v.result then
            machine.output[v.result] = v.result_count or 1
        end

        v.ingredients = (v.normal and v.normal.ingredients) or v.ingredients
        for kk, vv in ipairs(v.ingredients) do
            if not vv.name then
                machine.input[vv[1]] = vv[2]
            else
                machine.input[vv.name] = vv.amount
            end
        end

        self.idx[v.name] = machine
    end
end

function readRecipes()
    local names = {
	    "demo-furnace-recipe",
        "demo-recipe",
        "demo-turret",
        "ammo",
		"capsule",
        "equipment",
		"fluid-recipe",
		"inserter",
        "module",
		"recipe",
		"turret",
        "circuit-network"
    }

    for i, name in ipairs(names) do
        data.var = name
        dofile(string.format("%s/%s.lua", RECIPE_HOME, name))
    end
end

-- ret {{"xxx", 22}, {"yy", 11}}
function parseIngredients(recipe)
    local ret = {}
    for i, ingredient in ipairs(recipe.ingredients) do
        local name, amount
        if not ingredient.name then
            -- 普通原料
            name, amount = ingredient[1], ingredient[2]
        else
            name, amount = ingredient.name, ingredient.amount
        end

        local _recipe = data.map[name]
        if not _recipe or _recipe.category == "smelting" or _recipe.category == "oil-processing" then
            -- 最低级材料
            if not ret[name] then
                ret[name] = 0
            end
            ret[name] = ret[name] + amount
        else
            -- 高级材料
            local res = parseIngredients(_recipe)
            for _i, _ingredient in ipairs(res) do
                local _name, _amount = _ingredient[1], _ingredient[2]
                if not ret[_name] then
                    ret[_name] = 0
                end
                ret[_name] = ret[_name] + _amount * amount / (_recipe.result_count or 1)
            end
        end
    end
    local ret_ = {}
    for name, amount in pairs(ret) do
        table.insert(ret_, {name, amount})
    end
    return ret_
end

function seps(num)
    local ret = ""
    for i = 1, num do
        ret = ret .. "    "
    end
    return ret
end

local langData = readLangCfg(string.format("%s/base.cfg", LOCALE_HOME))

function lang(key, subKey)
    if not subKey then
        subKey = "name"
    end
    local str = ""
    if langData[subKey][key] then
        str = langData[subKey][key]
    else
        str = "<" .. key .. ">"
    end
    return str
end


function parseIngredient(ingredient, n)
    if not n then
        n = 1
    end
    local str = ""
    local name, amount
    if not ingredient.name then
        -- 普通原料
        name, amount = ingredient[1], ingredient[2]
    else
        name, amount = ingredient.name, ingredient.amount
    end
    if data.map[name] then
        str = string.format("<div style=\"margin-left:%gpx;\"><a href=\"#%s\">%s</a> %g</div><!--%s-->", 40 * n, name, lang(name), amount, name)
    else
        str = string.format("<div style=\"margin-left:%gpx;\">%s %g</div><!--%s-->", 40 * n, lang(name), amount, name)
    end
    --print("@D@ ", str)
    return str
end

function parseResults(results)
    --print("@D|results", results)
    local str = ""
    for i, result in ipairs(results) do
        --print("@@@", result.name, result.type)
        if i > 1 then
            str = str .. "\n"
        end
        str = str .. seps(1) .. parseIngredient(result)
    end
    return str
end

function parseIcon(recipe)
    local str = ""
    if not recipe.icon then
        str = string.format("%s/%s.png", ICON_HOME, recipe.name)
        local f = io.open(str, "rb")
        if not f then
            str = string.format("%s/fluid/%s.png", ICON_HOME, recipe.name)
        else
            f:close()
        end
    else
        local pos = recipe.icon:find("/graphics/icons")
        str = string.format("%s/%s", ICON_HOME, recipe.icon:sub(pos + 16, #recipe.icon))
    end
    return str
end

function solution(name)
    local str = ""
    local res = solve(name)
    str = str .. seps(1) .. "<div style=\"margin-left:40px;\"><i>[machine]</i></div>\n"
    for k, v in pairs(res.mpool) do
        str = str .. seps(2) .. parseIngredient({k, v}, 2) .. "\n"
    end

    str = str .. seps(1) .. "<div style=\"margin-left:40px;\"><i>[material]</i></div>\n"
    for k, v in pairs(res.ipool) do
        str = str .. seps(2) .. parseIngredient({k, v}, 2) .. "\n"
    end
    return str
end

function parseRecipes()
    print("<html>\n")
    print("<head><meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\"/><title>Factorio配方</title></head>")
    print("<body>")
    for name, recipes in pairs(data.recipes) do
        -- 类别名
        print(string.format("<div><b><span style=\"font-size: 24px;\">===== %s =====</span></b></div><div><br/></div>\n", name))
        for j, recipe in ipairs(recipes) do
            local str = ""
            if recipe.type == "recipe" then
                --print("@D@|recipe", recipe.name)
                -- 配方名
                str = string.format("<div><a name=\"%s\"><b><span style=\"font-size: 18px;\">%s</span></b></a></div>", recipe.name, lang(recipe.name)) .. "\n"
                str = str .. string.format("<img src=\"%s\" />", parseIcon(recipe)) .. "\n"

                -- 输入
                str = str .. "<div><i><span style=\"font-size: 10px;\">[IN]</i></div>\n"
                for k, ingredient in ipairs(recipe.ingredients) do
                    str = str .. seps(1) .. parseIngredient(ingredient) .. "\n"
                end

                -- 总计输入
                str = str .. "<div><i><span style=\"font-size: 10px;\">[IN ALL]</i></div>\n"
                local ingredients = parseIngredients(recipe)
                for k, ingredient in ipairs(ingredients) do
                    str = str .. seps(1) .. parseIngredient(ingredient) .. "\n"
                end

                -- 输出
                str = str .. "<div><i><span style=\"font-size: 10px;\">[OUT]</i></div>\n"
                if recipe.result then
                    if data.map[recipe.name] then
                        str = str .. seps(1) .. string.format("<div style=\"margin-left:40px;\"><a href=\"#%s\">%s</a> %g</div>", recipe.result, lang(recipe.result), recipe.result_count or 1)
                    else
                        str = str .. seps(1) .. string.format("<div style=\"margin-left:40px;\">%s %g</div>", lang(recipe.result), recipe.result_count or 1)
                    end
                elseif recipe.results then
                    str = str .. parseResults(recipe.results)
                end

                -- 耗时
                str = str .. "<div><i><span style=\"font-size: 10px;\">[TIME]</i></div>\n"
                str = str .. seps(1) .. string.format("<div style=\"margin-left:40px;\">%g</div>", recipe.energy_required or 0.5)

                -- 最佳配比
                str = str .. "<div><i><span style=\"font-size: 10px;\">[SOLVE]</i></div>\n"
                str = str .. solution(recipe.name)

                str = str .. "<div><br/></div>\n<div><br/></div>\n"
            end
            print(str)
        end
    end
    print("</body>")
    print("</html>")
end

-- mpool: {["basic-xx"] = 2, ..}
-- ipool: {["iron-plate"] = 100, ..}
function simulate(mpool, ipool, duration)
    local machines = {}  -- 机器信息表
    for name, amount in pairs(mpool) do
        local item = data.idx[name]

        -- 常量
        for i = 1, amount do
            local machine = {
                name = name,
                output = {},
                time = item.time,
                input = {}
            }
            for k, v in pairs(item.output) do
                machine.output[k] = v
            end

            -- 变量
            machine._time = 0
            machine._end = false
            for k, v in pairs(item.input) do
                machine.input[k] = {
                    input = v,
                    _input = 0
                }
            end

            -- 统计变量
            machine.stat = {
                idle = 0,  -- 总共空闲时间
            }
            
            table.insert(machines, machine)
        end
    end

    -- 模拟，多次检查，直到材料池没有新增物品
    printf("模拟开始")
    printf("")

    local interval = 0.5
    for time = interval, duration, interval do
        printf("时间(%g/%g)", time, duration)
        printf("")
        local newItem
        local notEndLeft = #machines
        repeat
            printf("本次轮询开始")
            printf("")
            newItem = false
            for i, machine in ipairs(machines) do
                printf("尝试操作机器(%d) 配置(%s)", i, lang(machine.name))
                if not machine._end then
                    printf("当前操作状态为 尚未操作")
                    if machine._time == 0 then
                        -- 该机器idle，尝试输入材料
                        printf("处于 空闲 状态")
                        local ready = true
                        for k, v in pairs(machine.input) do
                            printf("检查原料 %s(%g/%g)", lang(k), v._input, v.input)
                            local need = v.input - v._input
                            if need > 0 then
                                printf("需要原料 %s(%g)", lang(k), need)
                                if not ipool[k] then
                                    ipool[k] = 0
                                end

                                if ipool[k] < need then
                                    printf("原料 %s 不足, 库存 %s(%g)", lang(k), lang(k), ipool[k])
                                    need = ipool[k]
                                    ready = false
                                end

                                -- 入料
                                if need > 0 then
                                    ipool[k] = ipool[k] - need
                                    v._input = v._input + need
                                    printf("加入 %s(%g) 后, %s(%g/%g), 库存 %s(%g)", lang(k), need, lang(k), v._input, v.input, lang(k), ipool[k])
                                else
                                    printf("库存中没有 %s", lang(k))
                                end
                            end
                        end

                        if ready then
                            -- 所有材料齐全，开机
                            printf("材料齐全, 开始生产")
                            machine._time = machine._time + interval
                            machine._end = true
                            notEndLeft = notEndLeft - 1
                            printf("操作结束，当前进度(%g/%g), %.1f%%", machine._time, machine.time, machine._time * 100 / machine.time)
                        end
                    else
                        -- 工作中的机器
                        printf("处于 生产 状态")
                        machine._time = machine._time + interval
                        machine._end = true
                        notEndLeft = notEndLeft - 1
                        printf("操作结束，当前进度(%g/%g), %.1f%%", machine._time, machine.time, machine._time * 100 / machine.time)
                    end
                else
                    printf("当前操作状态为 已操作")
                end

                -- 检查该机器生产进度
                if machine._end and machine._time >= machine.time then
                    printf("有产物, 材料已消耗, 进度已清零")
                    for k, v in pairs(machine.input) do
                        v._input = 0
                    end
                    machine._time = 0

                    for k, v in pairs(machine.output) do
                        if not ipool[k] then
                            ipool[k] = 0
                        end
                        printf("产物 %s(%g) 进入库存", lang(k), machine.output[k])
                        ipool[k] = ipool[k] + machine.output[k]
                    end

                    if not newItem then
                        printf("库存有新增材料, 可能需要追加一次轮询")
                        newItem = true
                    end
                end

                printf("")

                if notEndLeft == 0 then
                    printf("没有空闲机器，将退出轮询")
                    printf("")
                    break
                end
            end
            printf("本次轮询结束")
            printf("")
        until not newItem or notEndLeft == 0

        printf("所有机器操作完毕")
        -- 统计机器状态，以及完成状态初始化
        for i, machine in ipairs(machines) do
            if machine._end then
                machine._end = false
            elseif machine._time == 0 then
                machine.stat.idle = machine.stat.idle + interval
                printf("机器(%d)总空闲(%g)", i, machine.stat.idle)
            end
        end
        printf("")
    end
    printf("")
    printf("模拟结束")
    printf("")

    -- 显示信息
    print("运作时间")
    print(seps(1) .. duration)
    print()
    print("机器信息")
    for i, machine in ipairs(machines) do
        if machine._time > 0 then
            for k, v in pairs(machine.input) do
                ipool[k] = ipool[k] + v._input
            end
        end
        
        print(seps(1) .. string.format("机器(%d) 配置(%s) 总空闲(%g)", i, lang(machine.name), machine.stat.idle))
    end
    print()

    print("材料池")
    for k, v in pairs(ipool) do
        print(seps(1) .. string.format("%s %g", lang(k), v))
    end
end

function solve(name, ipoolmatch)
    -- nps: number per second
    -- ipoolmatch: {["item1"] = true, ..}
    -- return: {mpool = {["machine1"] = 1, ..}, ipool = {["item1"] = 2}}
    local function _solve(name, ipoolmatch, nps, mpool, ipool)
        local function addToPool(pool, name, amount)
            if pool[name] then
                pool[name] = pool[name] + amount
            else
                pool[name] = amount
            end
        end

        local needMachine = data.idx[name]
        if not needMachine or not needMachine.output[name] then
            return
        end
        local needMachineNps = needMachine.output[name] / needMachine.time  -- nps for output

        if not nps then
            nps = needMachineNps
        end

        -- 添加需要的机器
        local needMachineNum = nps / needMachineNps
        addToPool(mpool, name, needMachineNum)

        for iname, iamount in pairs(needMachine.input) do
            local inps = iamount / needMachine.time * needMachineNum  -- item need num per sec
            if ipoolmatch[iname] then
                -- 基础材料
                addToPool(ipool, iname, inps)
            else
                -- 需要机器加工的材料
                _solve(iname, ipoolmatch, inps, mpool, ipool)
            end
        end
    end

    local ret = {mpool = {}, ipool = {}}
    if not ipoolmatch then
        ipoolmatch = {["copper-ore"] = true, ["iron-ore"] = true, ["coal"] = true, ["stone"] = true, ["stone-brick"] = true, ["steel-plate"] = true, ["copper-plate"] = true, ["iron-plate"] = true, ["water"] = true, ["petroleum-gas"] = true, ["alien-artifact"] = true}
    end
    _solve(name, ipoolmatch, nil, ret.mpool, ret.ipool)

    local n = 0
    local ok
    repeat
        n = n + 1
        ok = true
        for name, amount in pairs(ret.mpool) do
            local m
            m, ok = toint(amount * n)
            if not ok then
                break
            end
        end

        if ok then
            for name, amount in pairs(ret.ipool) do
                local m
                m, ok = toint(amount * n)
                if not ok then
                    break
                end
            end
        end
    until ok or n >= 1000

    if ok then
        for name, amount in pairs(ret.mpool) do
            ret.mpool[name] = toint(amount * n)
        end

        for name, amount in pairs(ret.ipool) do
            ret.ipool[name] = toint(amount * n)
        end

        return ret
    else
        printf("!n(%g)", n)
    end

    return ret
end

readRecipes()
--print(vardump(data.recipes, "recipes"))
parseRecipes()
--[[
simulate({
    ["electronic-circuit"] = 2,
    ["copper-cable"] = 3,
    ["basic-transport-belt"] = 1,
    ["iron-gear-wheel"] = 3,
    ["basic-inserter"] = 2,
    ["science-pack-2"] = 24
}, {
    ["copper-plate"] = 100000,
    ["iron-plate"] = 100000
}, 60)
]]

--local res = solve("steel-plate")
--printf("vardump\n%s", vardump(res, "solve"))
