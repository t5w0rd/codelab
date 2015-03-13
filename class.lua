function class(super)
    local meta = {}
    setmetatable(meta, super)
    
    meta.__index = super
    meta.__call = function (self, ...)
        return self:new(...)
    end

    local cls = {}
    setmetatable(cls, meta)

    cls.__index = cls
    cls._super = super
    
    function cls:_alloc()
        local meta = {}
        setmetatable(meta, self)
        
        meta.__index = function (self_, key)
            local tmp = rawget(self, key)
            if tmp then
                return tmp
            end

            tmp = rawget(self, '_super')
            if tmp then
                return tmp[key]
            end

            return nil
        end

        local obj = {}
        setmetatable(obj, meta)

        return obj
    end

    function cls:new(...)
        local obj = self:_alloc()

        obj._class = self

        if super then
            obj.super = super:_alloc()
        end

        if obj._init then
            obj:_init(...)
        end

        return obj
    end

    return cls
end

