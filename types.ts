
export enum ArtifactType {
  UserStory = "User Story",
  Bug = "Bug",
  Feature = "Feature",
  Epic = "Epic",
}

export interface HistoryItem {
  id: string;
  title: string;
  generatedDate: string;
  content: string;
  type: ArtifactType;
}
