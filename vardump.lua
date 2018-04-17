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

