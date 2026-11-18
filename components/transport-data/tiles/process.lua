node_keys = { "place" }

way_keys = {
	"highway",
	"waterway",
	"natural",
	"landuse",
	"leisure",
	"building"
}

function node_function()
	local place = Find("place")
	if place ~= "" then
		Layer("place")
		Attribute("class", place)
		Attribute("name", Find("name"))
	end
end

function way_function()
	local highway = Find("highway")
	if highway ~= "" then
		Layer("transportation", false)
		Attribute("class", highway)
		local name = Find("name")
		if name ~= "" then
			Attribute("name", name)
		end
	end

	local waterway = Find("waterway")
	if waterway ~= "" then
		Layer("waterway", false)
		Attribute("class", waterway)
		Attribute("name", Find("name"))
	end

	if Find("natural") == "water" or Find("landuse") == "reservoir" then
		Layer("water", true)
		Attribute("class", Find("water"))
		Attribute("name", Find("name"))
	end

	local landuse = Find("landuse")
	if landuse ~= "" then
		Layer("landuse", true)
		Attribute("class", landuse)
		Attribute("name", Find("name"))
	end

	if Find("building") ~= "" then
		Layer("building", true)
	end
end
