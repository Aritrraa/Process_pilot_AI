import re

with open('src/pages/Analytics.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove `<>` at line 206
content = content.replace("{activeTab === 'overview' && (\n        <>\n          {/* Stats */}", "{activeTab === 'overview' && (\n          {/* Stats */}")

# 2. Add `)}` after `</div>` at line 318
content = content.replace("""                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* LLM Cost & Usage */}""", """                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      )}

      {/* LLM Cost & Usage */}""")

# 3. Add `activeTab === 'overview' && ` to the other sections
content = content.replace("{data.llm_usage && (", "{activeTab === 'overview' && data.llm_usage && (")
content = content.replace("{(data.department_activity || []).length > 0 && (", "{activeTab === 'overview' && (data.department_activity || []).length > 0 && (")
content = content.replace("{data.team_workload?.length > 0 && (", "{activeTab === 'overview' && data.team_workload?.length > 0 && (")
content = content.replace("{(data.documentation_health !== undefined) && (", "{activeTab === 'overview' && (data.documentation_health !== undefined) && (")
content = content.replace("{(data.latest_searches || []).length > 0 && (", "{activeTab === 'overview' && (data.latest_searches || []).length > 0 && (")
content = content.replace("{data.team_details && (", "{activeTab === 'overview' && data.team_details && (")

with open('src/pages/Analytics.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Analytics.jsx patched!")
