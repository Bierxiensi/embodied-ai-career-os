/** 星级渲染组件。
 * level 0-5 对应 MY_CONTEXT 星级，达到 targetLevel 显示满星实色，未达显示空星。
 * 抽出为独立组件，供 SkillCard 等多处复用，避免重复实现。
 */
type Props = {
  level: number; // 当前等级 0-5
  total?: number; // 总星数，默认 5
};

const FULL = "★";
const EMPTY = "☆";

export default function StarRating({ level, total = 5 }: Props) {
  const stars = Array.from({ length: total }, (_, i) =>
    i < level ? FULL : EMPTY
  );
  return (
    <span className="font-mono text-amber-500 tracking-tight" aria-label={`${level}/${total}`}>
      {stars.join("")}
    </span>
  );
}
