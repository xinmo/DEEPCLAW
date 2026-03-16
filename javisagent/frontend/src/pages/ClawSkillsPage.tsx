import React, { useEffect, useState } from "react";
import {
  Button,
  Card,
  Divider,
  Drawer,
  Empty,
  Grid,
  Input,
  Segmented,
  Space,
  Spin,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import ReactMarkdown from "react-markdown";

import { clawApi } from "../services/clawApi";
import type { ClawSkillDetail, ClawSkillsStats, ClawSkillSummary } from "../types/claw";

const { useBreakpoint } = Grid;
const { Paragraph, Text, Title } = Typography;

type SkillFilter = "all" | "enabled" | "disabled";

const SKILL_FRONTMATTER_PATTERN = /^---\r?\n[\s\S]*?\r?\n---\r?\n?/;

function stripSkillFrontmatter(content: string) {
  return content.replace(SKILL_FRONTMATTER_PATTERN, "").trimStart();
}

const ClawSkillsPage: React.FC = () => {
  const screens = useBreakpoint();
  const isNarrowLayout = !screens.xl;
  const [skills, setSkills] = useState<ClawSkillSummary[]>([]);
  const [stats, setStats] = useState<ClawSkillsStats>({ total: 0, enabled: 0, disabled: 0 });
  const [selectedSkillName, setSelectedSkillName] = useState<string>("");
  const [selectedSkill, setSelectedSkill] = useState<ClawSkillDetail | null>(null);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [filter, setFilter] = useState<SkillFilter>("all");
  const [listLoading, setListLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [updatingSkillName, setUpdatingSkillName] = useState<string | null>(null);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);

  useEffect(() => {
    void loadSkills();
  }, []);

  useEffect(() => {
    if (!selectedSkillName) {
      setSelectedSkill(null);
      return;
    }
    void loadSkillDetail(selectedSkillName);
  }, [selectedSkillName]);

  const loadSkills = async () => {
    try {
      setListLoading(true);
      const data = await clawApi.listSkills();
      setSkills(data.skills);
      setStats(data.stats);
      if (data.skills.length > 0) {
        setSelectedSkillName((current) => {
          if (current && data.skills.some((skill) => skill.name === current)) {
            return current;
          }
          return data.skills[0].name;
        });
      } else {
        setSelectedSkillName("");
      }
    } catch (error) {
      message.error("加载技能列表失败");
      console.error(error);
    } finally {
      setListLoading(false);
    }
  };

  const loadSkillDetail = async (skillName: string) => {
    try {
      setDetailLoading(true);
      const detail = await clawApi.getSkillDetail(skillName);
      setSelectedSkill(detail);
    } catch (error) {
      message.error("加载技能详情失败");
      console.error(error);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSelectSkill = (skillName: string) => {
    setSelectedSkillName(skillName);
    if (isNarrowLayout) {
      setDetailDrawerOpen(true);
    }
  };

  const handleToggleSkill = async (skillName: string, enabled: boolean) => {
    try {
      setUpdatingSkillName(skillName);
      await clawApi.updateSkillStatus(skillName, enabled);
      message.success(enabled ? "技能已启用" : "技能已禁用");
      await loadSkills();
      if (selectedSkillName === skillName) {
        await loadSkillDetail(skillName);
      }
    } catch (error) {
      message.error("更新技能状态失败");
      console.error(error);
    } finally {
      setUpdatingSkillName(null);
    }
  };

  const filteredSkills = skills.filter((skill) => {
    const matchesKeyword =
      skill.name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
      skill.description.toLowerCase().includes(searchKeyword.toLowerCase());
    const matchesFilter =
      filter === "all" ||
      (filter === "enabled" && skill.enabled) ||
      (filter === "disabled" && !skill.enabled);
    return matchesKeyword && matchesFilter;
  });

  const renderSkillDetail = (skill: ClawSkillDetail | null) => {
    if (detailLoading) {
      return (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spin />
        </div>
      );
    }

    if (!skill) {
      return <Empty description="选择一个技能查看详情" style={{ marginTop: 48 }} />;
    }

    const previewContent = stripSkillFrontmatter(skill.content);

    return (
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 16,
              flexWrap: "wrap",
            }}
          >
            <div>
              <Title level={4} style={{ marginTop: 0, marginBottom: 8 }}>
                {skill.name}
              </Title>
              <Space wrap size={[8, 8]}>
                <Tag color={skill.enabled ? "green" : "default"}>
                  {skill.enabled ? "已启用" : "已禁用"}
                </Tag>
                {skill.version ? <Tag>{skill.version}</Tag> : null}
                {skill.declared_name && skill.declared_name !== skill.name ? (
                  <Tag>{skill.declared_name}</Tag>
                ) : null}
              </Space>
            </div>
            <Switch
              checked={skill.enabled}
              checkedChildren="启用"
              unCheckedChildren="禁用"
              loading={updatingSkillName === skill.name}
              onChange={(checked) => void handleToggleSkill(skill.name, checked)}
            />
          </div>
          <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
            {skill.description}
          </Paragraph>
        </div>

        <div>
          <Text strong>路径</Text>
          <Paragraph copyable style={{ marginBottom: 8 }}>
            {skill.path}
          </Paragraph>
          {skill.compatibility ? (
            <Paragraph style={{ marginBottom: 8 }}>
              <Text strong>兼容性：</Text>
              {skill.compatibility}
            </Paragraph>
          ) : null}
          {skill.license ? (
            <Paragraph style={{ marginBottom: 8 }}>
              <Text strong>License：</Text>
              {skill.license}
            </Paragraph>
          ) : null}
          {skill.allowed_tools.length > 0 ? (
            <Space wrap>
              <Text strong>推荐工具：</Text>
              {skill.allowed_tools.map((tool) => (
                <Tag key={tool}>{tool}</Tag>
              ))}
            </Space>
          ) : null}
        </div>

        <div>
          <Text strong>SKILL.md</Text>
          <Divider style={{ margin: "8px 0 16px" }} />
          <Tabs
            defaultActiveKey="preview"
            items={[
              {
                key: "preview",
                label: "Markdown 预览",
                children: (
                  <div
                    style={{
                      maxHeight: isNarrowLayout ? "60vh" : "70vh",
                      overflow: "auto",
                      padding: 16,
                      border: "1px solid #f0f0f0",
                      borderRadius: 12,
                      background: "#fafafa",
                    }}
                  >
                    {previewContent ? (
                      <ReactMarkdown>{previewContent}</ReactMarkdown>
                    ) : (
                      <Empty description="SKILL.md 没有可预览的正文内容" style={{ margin: "24px 0" }} />
                    )}
                  </div>
                ),
              },
              {
                key: "raw",
                label: "原文",
                children: (
                  <pre
                    style={{
                      margin: 0,
                      maxHeight: isNarrowLayout ? "60vh" : "70vh",
                      overflow: "auto",
                      padding: 16,
                      border: "1px solid #f0f0f0",
                      borderRadius: 12,
                      background: "#0f172a",
                      color: "#e2e8f0",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontFamily: "Consolas, Monaco, monospace",
                      fontSize: 13,
                      lineHeight: 1.6,
                    }}
                  >
                    {skill.content}
                  </pre>
                ),
              },
            ]}
          />
        </div>
      </Space>
    );
  };

  return (
    <>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: isNarrowLayout ? "minmax(0, 1fr)" : "360px minmax(0, 1fr)",
          gap: 24,
          alignItems: "start",
        }}
      >
        <div
          style={{
            minWidth: 0,
            border: "1px solid #f0f0f0",
            borderRadius: 12,
            background: "#fff",
            overflow: "hidden",
          }}
        >
          <div style={{ padding: 16, borderBottom: "1px solid #f0f0f0" }}>
            <Title level={5} style={{ margin: 0 }}>
              技能
            </Title>
            <Text type="secondary">
              管理 Claw 当前可见的全局 skills，支持启用、禁用和只读查看。
            </Text>
            <Space wrap style={{ marginTop: 12 }}>
              <Tag>{`${stats.total} skills`}</Tag>
              <Tag color="green">{`${stats.enabled} enabled`}</Tag>
              <Tag>{`${stats.disabled} disabled`}</Tag>
            </Space>
          </div>

          <div style={{ padding: 16, borderBottom: "1px solid #f0f0f0" }}>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <Input
                placeholder="搜索技能名称或描述"
                value={searchKeyword}
                onChange={(event) => setSearchKeyword(event.target.value)}
                allowClear
              />
              <Segmented<SkillFilter>
                block
                value={filter}
                onChange={(value) => setFilter(value)}
                options={[
                  { label: "全部", value: "all" },
                  { label: "已启用", value: "enabled" },
                  { label: "已禁用", value: "disabled" },
                ]}
              />
            </Space>
          </div>

          <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            {listLoading ? (
              <div style={{ textAlign: "center", padding: 32 }}>
                <Spin />
              </div>
            ) : filteredSkills.length === 0 ? (
              <Empty description="没有匹配的技能" style={{ margin: "32px 0" }} />
            ) : (
              filteredSkills.map((skill) => {
                const selected = skill.name === selectedSkillName;

                return (
                  <Card
                    key={skill.name}
                    hoverable
                    onClick={() => handleSelectSkill(skill.name)}
                    styles={{
                      body: { padding: 16 },
                    }}
                    style={{
                      borderColor: selected ? "#91caff" : "#f0f0f0",
                      background: selected ? "#f0f7ff" : "#fff",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        gap: 12,
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: 15,
                            fontWeight: 600,
                            lineHeight: 1.4,
                            wordBreak: "break-word",
                          }}
                        >
                          {skill.name}
                        </div>
                        <Space wrap size={[8, 8]} style={{ marginTop: 8 }}>
                          <Tag color={skill.enabled ? "green" : "default"}>
                            {skill.enabled ? "已启用" : "已禁用"}
                          </Tag>
                          {skill.version ? <Tag>{skill.version}</Tag> : null}
                        </Space>
                      </div>
                      <Switch
                        checked={skill.enabled}
                        loading={updatingSkillName === skill.name}
                        onClick={(_, event) => event.stopPropagation()}
                        onChange={(checked) => void handleToggleSkill(skill.name, checked)}
                      />
                    </div>

                    <Paragraph
                      type="secondary"
                      ellipsis={{ rows: 3 }}
                      style={{ marginTop: 12, marginBottom: 12 }}
                    >
                      {skill.description}
                    </Paragraph>

                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {skill.path}
                    </Text>

                    <div style={{ marginTop: 12 }}>
                      <Button
                        type="link"
                        style={{ padding: 0 }}
                        onClick={(event) => {
                          event.stopPropagation();
                          handleSelectSkill(skill.name);
                        }}
                      >
                        查看详情
                      </Button>
                    </div>
                  </Card>
                );
              })
            )}
          </div>
        </div>

        {!isNarrowLayout ? (
          <div
            style={{
              minWidth: 0,
              border: "1px solid #f0f0f0",
              borderRadius: 12,
              background: "#fff",
              padding: 24,
            }}
          >
            {renderSkillDetail(selectedSkill)}
          </div>
        ) : null}
      </div>

      {isNarrowLayout ? (
        <Drawer
          title={selectedSkill?.name || "技能详情"}
          placement="right"
          width="100%"
          open={detailDrawerOpen}
          onClose={() => setDetailDrawerOpen(false)}
        >
          {renderSkillDetail(selectedSkill)}
        </Drawer>
      ) : null}
    </>
  );
};

export default ClawSkillsPage;
